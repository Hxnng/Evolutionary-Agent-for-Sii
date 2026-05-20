"""Shared evaluation mode helpers.

The evaluator scripts stay dataset-specific for loading/scoring, while this
module centralizes the run-mode policy: which learned skill directory to use
and whether reflection is allowed to write updates.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


DATASET_LEARNED_SKILLS = {
    "simplevqa": "simplevqa_learned_skills",
    "2wiki": "2wiki_learned_skills",
    "benchmark": "benchmark_learned_skills",
}


@dataclass(frozen=True)
class EvaluationMode:
    run_mode: str
    test_mode: str
    reflection: bool
    skills_dir: str
    learned_skills_dir: str

    @property
    def label(self) -> str:
        skill_label = "learned" if self.test_mode == "learned" else "from_scratch"
        reflection_label = "reflection" if self.reflection else "no_reflection"
        return f"{self.run_mode}_{skill_label}_{reflection_label}"


def add_mode_args(parser: argparse.ArgumentParser, *, dataset_name: str | None) -> None:
    default_learned = DATASET_LEARNED_SKILLS.get(dataset_name or "", "<dataset>_learned_skills")
    parser.add_argument(
        "--run-mode",
        choices=["train", "test"],
        default="test",
        help="train writes/refines skills; test evaluates a chosen skill policy.",
    )
    parser.add_argument(
        "--test-mode",
        choices=["learned", "from-scratch"],
        default="learned",
        help="In test mode, load trained skills or start with an empty learned-skill directory.",
    )
    parser.add_argument(
        "--reflection",
        choices=["on", "off"],
        default=None,
        help="Enable/disable reflector skill updates. Defaults to on for train and learned-skill test, off for from-scratch test.",
    )
    parser.add_argument(
        "--skills-dir",
        default="skills",
        help="Seed skill directory. Usually keep this as skills.",
    )
    parser.add_argument(
        "--learned-skills-dir",
        default=None,
        help=f"Override learned skill directory. Default: {default_learned}.",
    )
    parser.add_argument(
        "--fresh-learned-skills-dir",
        default=None,
        help="Directory used when starting from scratch. Defaults under the trajectory directory.",
    )


def resolve_mode(
    args: argparse.Namespace,
    *,
    dataset_name: str,
    trajectory_dir: Path,
) -> EvaluationMode:
    run_mode = args.run_mode
    test_mode = args.test_mode
    if run_mode == "train":
        test_mode = "from-scratch"

    reflection = args.reflection
    if reflection is None:
        reflection_enabled = run_mode == "train" or test_mode == "learned"
    else:
        reflection_enabled = reflection == "on"
    if run_mode == "test" and not reflection_enabled:
        test_mode = "from-scratch"

    if test_mode == "learned":
        learned_dir = args.learned_skills_dir or DATASET_LEARNED_SKILLS[dataset_name]
    else:
        learned_dir = (
            args.learned_skills_dir
            or args.fresh_learned_skills_dir
            or str(trajectory_dir / "_fresh_learned_skills")
        )

    return EvaluationMode(
        run_mode=run_mode,
        test_mode=test_mode,
        reflection=reflection_enabled,
        skills_dir=str(args.skills_dir),
        learned_skills_dir=str(learned_dir),
    )
