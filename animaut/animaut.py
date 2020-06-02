import manimlib.imports as mn
import numpy as np
import pathlib
import pygraphviz as pgv
from pylatex.utils import escape_latex


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
    Compute the ratio and shift by wich we need to rescale and move the graph's
    graphviz positions so that it fits in manim's scene.
    """
    # 'bb' is the graphviz bounding box with the lower-left (ll) and upper-right
    # (ur) points
    llx, lly, urx, ury = map(float, graph.graph_attr["bb"].split(","))
    width = urx - llx
    height = ury - lly

    # the scaling ratio
    ratio = min(mn.FRAME_WIDTH / width, mn.FRAME_HEIGHT / height)

    center = np.array([(urx + llx) * ratio / 2, (ury + lly) * ratio / 2, 0])

    return ratio, -center


DEBUG_RENDERED_GRAPHS = 0


def dot_to_vgroup(source):
    """
    Generate a VGroup that manim can render to represent the dot graph

    This uses the graphviz's dot engine to establish a layout of the nodes and
    edges before creating manim's Circle (for the nodes) and VMobject (for the
    edges) using the positions given by that layout
    """
    A = pgv.AGraph(source)
    A.layout(prog="dot")

    # DEBUG: draw the dot layout in png files
    global DEBUG_RENDERED_GRAPHS
    pathlib.Path("media/graphs").mkdir(parents=True, exist_ok=True)
    A.draw(f"media/graphs/{DEBUG_RENDERED_GRAPHS}.png")
    DEBUG_RENDERED_GRAPHS += 1

    ratio, shift = scale_ratio_and_shift(A)

    # spawn each node in manim using the graphviz positions and our rescaling
    # ratio
    mnodes = []
    for node in A.iternodes():
        # 'point' shaped nodes aren't real nodes, they often represent the
        # origin of the arrow of an initial stat or the destination of the
        # arrow of a final state
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
        # edge.attr['pos'] contains a list of spline control points of the
        # form: 'e,x1,y1 x2,y2 x3,y3 x4,y4 […]'
        spline_points = [
            np.array([float(x) * ratio, float(y) * ratio, 0])
            for x, y in [point.split(",") for point in edge.attr["pos"][2:].split()]
        ]
        # graphviz generates a path that loops when rendered by manim, we
        # prevent that looping by removing the first control point
        del spline_points[0]

        # Try to translate graphviz color to manim, fallback to white
        color = dot_to_manim_colors.get(edge.attr.get("color", "white"), mn.WHITE)

        # Render the edge's label and path
        # TODO: we should use `.set_points_smoothly` but the spline control
        # points given by graphviz aren't used properly by manim, the result is
        # understandable but a bit chaotic
        mpath = mn.VMobject(color=color).set_points_as_corners(spline_points)
        if "label" in edge.attr and edge.attr["label"]:
            (labelx, labely) = map(float, edge.attr["lp"].split(","))
            mlabel = mn.TextMobject(escape_latex(edge.attr["label"]))
            mlabel.scale(0.65)
            mlabel.move_to(np.array([labelx * ratio, labely * ratio, 0]))
            medges.append(mn.VGroup(mpath, mlabel))
        else:
            medges.append(mpath)

    # Finally assemble into a VGroup and shift it to the center of scene
    return mn.VGroup(*mnodes, *medges).shift(shift)
