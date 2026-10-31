from manim import Rotate


def spin(scene, ctx):
    scene.play(Rotate(ctx.world.get("P"), angle=3.14), run_time=0.4)
