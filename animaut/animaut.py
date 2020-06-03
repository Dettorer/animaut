import manimlib.imports as mn
import math
import numpy as np
import pathlib
import pygraphviz as pgv
from dataclasses import dataclass
from pylatex.utils import escape_latex
from typing import List


class ANode(mn.Circle):
    """
    An automaton node to be rendered by manim
    """

    CONFIG = {
        "radius": 0.3,
    }


dot_to_manim_colors = {
    "white": mn.WHITE,
    "DimGray": mn.LIGHT_COLOR,
    "": mn.WHITE,
    "lightgray": mn.LIGHT_COLOR,
}


def scale_ratio_and_shift(graph):
    """
    Compute the ratio and shift by wich we need to rescale and move the graph's graphviz
    positions so that it fits in manim's scene.
    """
    # 'bb' is the graphviz bounding box with the lower-left (ll) and upper-right (ur)
    # points
    llx, lly, urx, ury = map(float, graph.graph_attr["bb"].split(","))
    width = urx - llx
    height = ury - lly

    ratio = min(mn.FRAME_WIDTH / width, mn.FRAME_HEIGHT / height)
    center = np.array([(urx + llx) * ratio / 2, (ury + lly) * ratio / 2, 0])

    return ratio, mn.ORIGIN - center


@dataclass
class Spline:
    # if present: there's an arrow head that goes from the first control point to
    # start_point
    start_point: np.array
    # if present: there's an arrow head that goes from the last control point to
    # end_point
    end_point: np.array
    # points through wich the curve must go
    anchor_points: List[np.array]
    # points that control the curvature of the curve
    handle_points: List[np.array]


def parse_graphviz_bspline(spline_str, ratio):
    """See https://www.graphviz.org/doc/info/attrs.html#k:splineType"""

    def parse_point(point):
        x, y = point.split(",")
        return np.array([float(x) * ratio, float(y) * ratio, 0])

    spline = Spline(None, None, [], [])

    points_str = spline_str.split()
    if points_str[0].startswith("s,"):
        # we have a start point
        spline.start_point = parse_point(points_str.pop(0)[2:])
    if points_str[0].startswith("e,"):
        # we have an end point
        spline.end_point = parse_point(points_str.pop(0)[2:])

    for i in range(0, len(points_str) - 1, 3):
        spline.anchor_points.append(parse_point(points_str[0]))
        spline.handle_points.append(parse_point(points_str[1]))
        spline.handle_points.append(parse_point(points_str[2]))
        spline.anchor_points.append(parse_point(points_str[3]))

    return spline


def segment_to_arrow(src: np.array, dst: np.array) -> mn.ArrowTip:
    """Create an ArrowTip that points from `src` to `dst`"""
    # TODO: it's not always really in the right direction, find out why
    delta_x = dst[0] - src[0]
    delta_y = dst[1] - src[1]
    angle = math.atan2(delta_y, delta_x) * 180 / math.pi
    angle *= mn.DEGREES
    return mn.ArrowTip(start_angle=angle, color=mn.WHITE).move_to(dst)


DEBUG_RENDERED_GRAPHS = 0


def dot_to_vgroup(source):
    """
    Generate a VGroup that manim can render to represent the dot graph

    This uses the graphviz's dot engine to establish a layout of the nodes and edges
    before creating manim's Circle (for the nodes) and VMobject (for the edges) using
    the positions given by that layout
    """
    A = pgv.AGraph(source)
    A.layout(prog="dot")

    # DEBUG: draw the dot layout in png files
    global DEBUG_RENDERED_GRAPHS
    pathlib.Path("media/graphs").mkdir(parents=True, exist_ok=True)
    A.draw(f"media/graphs/{DEBUG_RENDERED_GRAPHS}.png")
    DEBUG_RENDERED_GRAPHS += 1

    ratio, shift = scale_ratio_and_shift(A)

    # spawn each node in manim using the graphviz positions and our rescaling ratio
    mnodes = []
    for node in A.iternodes():
        # 'point' shaped nodes aren't real nodes, they often represent the origin of the
        # arrow of an initial stat or the destination of the arrow of a final state
        if node.attr["shape"] == "point":
            continue

        x, y = map(lambda s: float(s), node.attr["pos"].split(","))
        pos = np.array([x * ratio, y * ratio, 0])

        # Try to translate graphviz color to manim, fallback to white
        color = dot_to_manim_colors.get(node.attr.get("fillcolor", "white"), mn.WHITE)

        # Render the node's label and circle
        mlabel = mn.TextMobject(escape_latex(node.name)).move_to(pos)
        mcircle = ANode(arc_center=pos, color=color)
        mnodes.append(mn.VGroup(mcircle, mlabel))

    # spawn each edges in a similar way
    medges = []
    for edge in A.edges():
        objects = []  # manim objects representing the edge

        spline = parse_graphviz_bspline(edge.attr["pos"], ratio)

        # Try to translate graphviz color to manim, fallback to white
        color = dot_to_manim_colors.get(edge.attr.get("color", "white"), mn.WHITE)

        # Render the edge's path using graphviz's control points
        mpath = mn.VMobject(color=color)
        if spline.start_point is not None:
            mpath.add_smooth_curve_to(spline.start_point)
        for i in range(0, len(spline.anchor_points), 2):
            mpath.add_cubic_bezier_curve(
                spline.anchor_points[i],
                spline.handle_points[i],
                spline.handle_points[i + 1],
                spline.anchor_points[i + 1],
            )
        if spline.end_point is not None:
            # TODO: this seems to be missing a handle point, the result is a bit jagged
            mpath.add_smooth_curve_to(spline.end_point)

        # Render the arrow heads, if any
        if spline.start_point is not None:
            objects.append(
                segment_to_arrow(spline.anchor_points[0], spline.start_point)
            )
        if spline.end_point is not None:
            objects.append(segment_to_arrow(spline.anchor_points[-1], spline.end_point))

        objects.append(mpath)
        if "label" in edge.attr and edge.attr["label"]:
            (labelx, labely) = map(float, edge.attr["lp"].split(","))
            mlabel = mn.TextMobject(escape_latex(edge.attr["label"]))
            mlabel.scale(0.65)
            mlabel.move_to(np.array([labelx * ratio, labely * ratio, 0]))
            objects.append(mlabel)

        medges.append(mn.VGroup(*objects))

    # Finally assemble into a VGroup and shift it to the center of scene
    return mn.VGroup(*mnodes, *medges).shift(shift)
