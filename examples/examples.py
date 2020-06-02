import manimlib.imports as mn
from animaut.animaut import dot_to_vgroup


class A_progression(mn.Scene):
    def construct(self):
        with open('examples/A.dot') as f:
            mA = dot_to_vgroup(f.read())
        with open('examples/A_complement.dot') as f:
            mA_complement = dot_to_vgroup(f.read())
        with open('examples/A_complement_trim.dot') as f:
            mA_complement_trim = dot_to_vgroup(f.read())

        self.play(mn.ShowCreation(mA))
        self.wait()
        self.remove(mA)
        self.play(mn.Transform(mA, mA_complement))
        self.wait()
        self.remove(mA)
        self.remove(mA_complement)
        self.play(mn.Transform(mA_complement, mA_complement_trim))

        self.wait()


class C_progression(mn.Scene):
    def construct(self):
        with open('examples/C1.dot') as f:
            mD = dot_to_vgroup(f.read())
        self.play(mn.ShowCreation(mD))
        self.wait()
        self.remove(mD)
        for n in range(2, 4):
            with open(f'examples/C{n}.dot') as f:
                next_mD = dot_to_vgroup(f.read())
            self.play(mn.Transform(mD, next_mD))
            self.wait()
            self.remove(mD)
            self.remove(next_mD)
            mD = next_mD
