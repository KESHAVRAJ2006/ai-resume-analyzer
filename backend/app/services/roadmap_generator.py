"""Turn a gap report into a concrete 4-week learning plan.

Design rules, in priority order:
  1. Critical gaps come first. Week 1 must move the score the most.
  2. At most three skills per week - a plan nobody can finish is not a plan.
  3. Never produce an empty week. A candidate with no gaps gets a depth plan
     (portfolio, testing, system design) instead of four blank cards.

The activities are generated from the skill's category, so adding a new skill
to skill_dictionary.csv automatically gets sensible steps without editing this
file.

PRIVACY: the plan is built from skills only and is guidance, not a hiring
decision.
"""

from dataclasses import dataclass

from app.services.gap_analyzer import GapReport, SkillGap

# Three skills a week at roughly 5 focused hours each is about 15 hours, or
# two hours a day - achievable alongside a full-time course load.
MAX_SKILLS_PER_WEEK = 3
HOURS_PER_SKILL = 5
WEEKS = 4

# Per-category study pattern: (how to learn it, what to build, how to prove it).
# Every template takes a single {skill} placeholder.
CATEGORY_PLAYBOOK: dict[str, tuple[str, str, str]] = {
    "Programming Languages": (
        "Work through the official {skill} tutorial and solve 20 small exercises",
        "Rebuild a program you already know in {skill} from scratch",
        "Push your {skill} exercises to GitHub with a README explaining your approach",
    ),
    "Web & Frontend": (
        "Follow the official {skill} docs and build three small components",
        "Rebuild one screen of a product you use daily with {skill}",
        "Deploy what you built with {skill} and check it on a phone-width screen",
    ),
    "Backend & APIs": (
        "Read the {skill} quickstart and build a CRUD API with four endpoints",
        "Add validation, error handling and pagination to that API using {skill}",
        "Document the {skill} endpoints and test each one with a client such as Postman",
    ),
    "Databases & Data Engineering": (
        "Learn the {skill} data model and load a real public dataset into it",
        "Write ten {skill} queries, from simple filters through joins to aggregates",
        "Make one slow {skill} query faster, and note what changed and why",
    ),
    "Machine Learning & AI": (
        "Study the {skill} fundamentals and reproduce one worked example end to end",
        "Apply {skill} to a dataset nobody has tutorialised, and evaluate honestly",
        "Write up your {skill} metrics, the failure cases and what you would try next",
    ),
    "Data Analysis & Visualization": (
        "Learn {skill} on a dataset you actually care about",
        "Produce one analysis with {skill} that answers a specific question",
        "Present your {skill} result in five slides aimed at a non-technical reader",
    ),
    "Cloud & DevOps": (
        "Work through the {skill} getting-started guide on a free tier account",
        "Use {skill} to deploy an app you have already built",
        "Document your {skill} setup so a teammate could repeat it from your notes",
    ),
    "Practices & Tools": (
        "Read a short guide to {skill} and apply it to a repository you own",
        "Use {skill} throughout one week of real work, not a toy example",
        "Write down the three {skill} habits you want to keep",
    ),
}

# Used when a category has no playbook entry, so a new category never crashes.
FALLBACK_PLAYBOOK: tuple[str, str, str] = (
    "Find the official {skill} documentation and work through the introduction",
    "Build one small project that uses {skill} for something real",
    "Publish a short write-up of what you learned about {skill}",
)

# The depth plan, used when there is nothing left to close.
DEPTH_PLAN: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "Deepen your strongest project",
        "Take the best project on your resume and make it production-grade.",
        (
            "Add error handling and input validation everywhere it is missing",
            "Write a README that explains the problem, not just the commands",
            "Record the before and after of one performance improvement",
        ),
    ),
    (
        "Prove it with tests",
        "Testing is the fastest way to look senior on a junior resume.",
        (
            "Add unit tests for the trickiest function in your project",
            "Add one end-to-end test that covers the main user journey",
            "Wire the tests into CI so they run on every push",
        ),
    ),
    (
        "Scale and design",
        "Show you can reason about systems, not only write functions.",
        (
            "Draw the architecture of your project and mark the bottleneck",
            "Write a one-page design doc for the next feature you would add",
            "Study two system design case studies and summarise the trade-offs",
        ),
    ),
    (
        "Communicate the work",
        "Unexplained work does not count in an interview.",
        (
            "Write a short post about the hardest bug you fixed and how",
            "Rewrite your resume bullets to lead with measurable outcomes",
            "Prepare a five-minute walkthrough of your best project",
        ),
    ),
)


@dataclass(frozen=True)
class RoadmapWeek:
    """One week of the plan, ready to render as a timeline node."""

    week: int
    title: str
    objective: str
    focus_skills: tuple[str, ...]   # canonical names, for chips on the node
    activities: tuple[str, ...]
    estimated_hours: int


def generate_roadmap(report: GapReport) -> list[RoadmapWeek]:
    """Take a gap report, return a 4-week plan ordered by impact.

    Always returns exactly 4 weeks: gaps first, then depth work once the gaps
    run out, so the timeline is never half empty.
    """
    # report.missing is already sorted critical -> important -> optional.
    batches = _split_into_weeks(list(report.missing))

    weeks: list[RoadmapWeek] = []
    for index in range(WEEKS):
        batch = batches[index] if index < len(batches) else []
        if batch:
            weeks.append(_week_from_gaps(index + 1, batch))
        else:
            weeks.append(_week_from_depth_plan(index + 1))
    return weeks


def _split_into_weeks(gaps: list[SkillGap]) -> list[list[SkillGap]]:
    """Take ordered gaps, return them chunked into at most 4 weekly batches.

    Anything beyond 12 skills is dropped on purpose: a 4-week plan that lists
    30 skills is a wish, and the extra items stay visible in the gap table.
    """
    capped = gaps[: WEEKS * MAX_SKILLS_PER_WEEK]
    return [
        capped[start : start + MAX_SKILLS_PER_WEEK]
        for start in range(0, len(capped), MAX_SKILLS_PER_WEEK)
    ]


def _week_from_gaps(week_number: int, gaps: list[SkillGap]) -> RoadmapWeek:
    """Take a week number and its skills, return a populated week."""
    names = [gap.canonical_name for gap in gaps]
    activities: list[str] = []
    for gap in gaps:
        learn, build, prove = CATEGORY_PLAYBOOK.get(gap.category, FALLBACK_PLAYBOOK)
        # One activity per skill keeps a three-skill week at three tasks rather
        # than nine, which is the difference between a plan and a fantasy.
        template = learn if gap.severity == "critical" else build
        activities.append(template.format(skill=gap.canonical_name))

    # The single highest-value task of the week, spelled out.
    headline = gaps[0]
    _, _, prove = CATEGORY_PLAYBOOK.get(headline.category, FALLBACK_PLAYBOOK)
    activities.append(prove.format(skill=headline.canonical_name))

    return RoadmapWeek(
        week=week_number,
        title=_week_title(names),
        objective=_week_objective(gaps),
        focus_skills=tuple(names),
        activities=tuple(activities),
        estimated_hours=len(gaps) * HOURS_PER_SKILL,
    )


def _week_from_depth_plan(week_number: int) -> RoadmapWeek:
    """Take a week number, return the depth-plan week for that slot."""
    title, objective, activities = DEPTH_PLAN[(week_number - 1) % len(DEPTH_PLAN)]
    return RoadmapWeek(
        week=week_number,
        title=title,
        objective=objective,
        focus_skills=(),
        activities=activities,
        estimated_hours=HOURS_PER_SKILL * 2,
    )


def _week_title(names: list[str]) -> str:
    """Take the week's skill names, return a short human title."""
    if len(names) == 1:
        return f"Learn {names[0]}"
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{names[0]}, {names[1]} and {names[2]}"


def _week_objective(gaps: list[SkillGap]) -> str:
    """Take the week's gaps, return one sentence saying why this week matters."""
    critical = [gap for gap in gaps if gap.severity == "critical"]
    if critical:
        noun = "requirement" if len(critical) == 1 else "requirements"
        return (
            f"Close {len(critical)} must-have {noun}. These carry the most weight, "
            "so this week moves your score the most."
        )
    if all(gap.severity == "optional" for gap in gaps):
        return "Polish. These skills differentiate you once the essentials are in place."
    return "Strengthen the skills that separate a shortlisted resume from a rejected one."
