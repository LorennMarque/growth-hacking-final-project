from __future__ import annotations

import argparse
import csv
import itertools
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


WEEKS = 14
DEFAULT_BUDGET = 60_000
DEFAULT_STEP = 100
ROUNDING_EPSILON = 1e-9

GIFT_HOURS_COST = 15_000
REVIEWS_COST = 12_000
BRANDING_COST = 10_000
REVIEW_SHARE_COST = 15_000

CINEMA_PROMOTER_WEEKLY_COST = 400
CINEMA_PRODUCTIVITY = 6
ORGANIC_INITIAL_WATCHERS = 25
ORGANIC_REFERRAL_RATE = 0.10
BRANDING_IMPACT = 0.02

STANDARD_RETENTION = [
    1.00,
    0.85,
    0.80,
    0.75,
    0.70,
    0.64,
    0.58,
    0.54,
    0.49,
    0.46,
    0.43,
    0.40,
    0.40,
    0.40,
]
SOCIAL_FEATURE_RETENTION = [
    1.00,
    0.8925,
    0.84,
    0.7875,
    0.735,
    0.672,
    0.609,
    0.567,
    0.5145,
    0.483,
    0.4515,
    0.42,
    0.42,
    0.42,
]

GIFT_LOOP_RATE = 0.20 * 3 * 0.70 * 0.30
GIFT_LOOP_MULTIPLIER = (1 / (1 - GIFT_LOOP_RATE)) - 1
REVIEWS_LOOP_MULTIPLIER = 0.035 * 3 * 50 * 0.25 * 0.01


@dataclass(frozen=True)
class Decisions:
    paid_media_weekly: int = 0
    cinema_activation_weekly: int = 0
    gift_hours: bool = False
    reviews: bool = False
    review_share: bool = False
    branding: bool = False

    @property
    def fixed_cost(self) -> int:
        return (
            (GIFT_HOURS_COST if self.gift_hours else 0)
            + (REVIEWS_COST if self.reviews else 0)
            + (REVIEW_SHARE_COST if self.review_share else 0)
            + (BRANDING_COST if self.branding else 0)
        )

    @property
    def total_investment(self) -> int:
        return self.fixed_cost + WEEKS * (
            self.paid_media_weekly + self.cinema_activation_weekly
        )


@dataclass(frozen=True)
class Simulation:
    decisions: Decisions
    new_watchers: list[int]
    retained_watchers: list[int]
    waw: list[int]
    paid_media_new: list[int]
    cinema_new: list[float]
    organic_new: list[float]
    gift_hours_new: list[int]
    reviews_new: list[int]

    @property
    def week_14_waw(self) -> int:
        return self.waw[-1]

    @property
    def total_waw(self) -> int:
        return sum(self.waw)


@dataclass(frozen=True)
class SearchResult:
    decisions: Decisions
    simulation: Simulation
    budget: int

    @property
    def spent(self) -> int:
        return self.decisions.total_investment

    @property
    def unspent(self) -> int:
        return self.budget - self.spent

    @property
    def week_14_waw(self) -> int:
        return self.simulation.week_14_waw

    @property
    def total_waw(self) -> int:
        return self.simulation.total_waw


def excel_round(value: float, digits: int = 0) -> int | float:
    """Replicate Excel ROUND for the positive values used by this model."""
    factor = 10**digits
    scaled = value * factor
    if scaled >= 0:
        rounded = math.floor(scaled + 0.5 + ROUNDING_EPSILON)
    else:
        rounded = math.ceil(scaled - 0.5 - ROUNDING_EPSILON)
    result = rounded / factor
    return int(result) if digits == 0 else result


def paid_media_new_watchers(weekly_investment: int) -> int:
    if weekly_investment <= 0:
        return 0
    return int(excel_round(math.log(weekly_investment * 0.1, 1.008) / 4))


def cinema_activation_new_watchers(weekly_investment: int) -> float:
    return weekly_investment / CINEMA_PROMOTER_WEEKLY_COST * CINEMA_PRODUCTIVITY


def retention_curve(review_share: bool) -> list[float]:
    return SOCIAL_FEATURE_RETENTION if review_share else STANDARD_RETENTION


def simulate(decisions: Decisions) -> Simulation:
    retention = retention_curve(decisions.review_share)
    paid_media_weekly_new = paid_media_new_watchers(decisions.paid_media_weekly)
    cinema_weekly_new = cinema_activation_new_watchers(
        decisions.cinema_activation_weekly
    )

    new_watchers: list[int] = []
    retained_watchers: list[int] = []
    waw: list[int] = []
    paid_media_new: list[int] = []
    cinema_new: list[float] = []
    organic_new: list[float] = []
    gift_hours_new: list[int] = []
    reviews_new: list[int] = []

    for week in range(WEEKS):
        previous_waw = waw[week - 1] if week > 0 else 0
        organic = (
            ORGANIC_INITIAL_WATCHERS
            if week == 0
            else previous_waw * ORGANIC_REFERRAL_RATE
        )
        gift = (
            int(excel_round(previous_waw * GIFT_LOOP_MULTIPLIER))
            if decisions.gift_hours and week > 0
            else 0
        )
        review = (
            int(excel_round(previous_waw * REVIEWS_LOOP_MULTIPLIER))
            if decisions.reviews and week > 0
            else 0
        )

        acquisitions_without_branding = (
            paid_media_weekly_new + cinema_weekly_new + organic + gift + review
        )
        branding_multiplier = 1 + BRANDING_IMPACT if decisions.branding and week < 12 else 1
        new = int(excel_round(acquisitions_without_branding * branding_multiplier))
        new_watchers.append(new)

        total_active = 0
        for cohort_week, cohort_size in enumerate(new_watchers):
            cohort_age = week - cohort_week
            total_active += int(excel_round(cohort_size * retention[cohort_age]))

        retained = total_active - new
        retained_watchers.append(retained)
        waw.append(total_active)

        paid_media_new.append(paid_media_weekly_new)
        cinema_new.append(cinema_weekly_new)
        organic_new.append(organic)
        gift_hours_new.append(gift)
        reviews_new.append(review)

    return Simulation(
        decisions=decisions,
        new_watchers=new_watchers,
        retained_watchers=retained_watchers,
        waw=waw,
        paid_media_new=paid_media_new,
        cinema_new=cinema_new,
        organic_new=organic_new,
        gift_hours_new=gift_hours_new,
        reviews_new=reviews_new,
    )


def exhaustive_search(
    budget: int = DEFAULT_BUDGET,
    step: int = DEFAULT_STEP,
    require_full_budget: bool = False,
) -> list[SearchResult]:
    results: list[SearchResult] = []
    feature_options = itertools.product([False, True], repeat=4)

    for gift_hours, reviews, review_share, branding in feature_options:
        fixed_decisions = Decisions(
            gift_hours=gift_hours,
            reviews=reviews,
            review_share=review_share,
            branding=branding,
        )
        fixed_cost = fixed_decisions.fixed_cost
        if fixed_cost > budget:
            continue

        remaining = budget - fixed_cost
        max_paid_units = remaining // (WEEKS * step)

        for paid_units in range(max_paid_units + 1):
            paid_weekly = paid_units * step
            remaining_after_paid = remaining - WEEKS * paid_weekly
            max_cinema_units = remaining_after_paid // (WEEKS * step)

            for cinema_units in range(max_cinema_units + 1):
                cinema_weekly = cinema_units * step
                decisions = Decisions(
                    paid_media_weekly=paid_weekly,
                    cinema_activation_weekly=cinema_weekly,
                    gift_hours=gift_hours,
                    reviews=reviews,
                    review_share=review_share,
                    branding=branding,
                )
                spent = decisions.total_investment
                if spent > budget:
                    continue
                if require_full_budget and spent != budget:
                    continue

                results.append(
                    SearchResult(
                        decisions=decisions,
                        simulation=simulate(decisions),
                        budget=budget,
                    )
                )

    return sorted(results, key=search_sort_key, reverse=True)


def search_sort_key(result: SearchResult) -> tuple[int, int, int]:
    return (result.week_14_waw, result.total_waw, result.spent)


def yes_no(value: bool) -> str:
    return "SI" if value else "NO"


def money(value: float | int) -> str:
    return f"USD {value:,.0f}".replace(",", ".")


def week_values(values: Iterable[float | int]) -> str:
    return ", ".join(f"W{index}: {value:.0f}" for index, value in enumerate(values, 1))


def result_row(result: SearchResult) -> dict[str, int | str]:
    decisions = result.decisions
    return {
        "week_14_waw": result.week_14_waw,
        "total_waw": result.total_waw,
        "spent": result.spent,
        "unspent": result.unspent,
        "paid_media_weekly": decisions.paid_media_weekly,
        "cinema_activation_weekly": decisions.cinema_activation_weekly,
        "gift_hours": yes_no(decisions.gift_hours),
        "reviews": yes_no(decisions.reviews),
        "review_share": yes_no(decisions.review_share),
        "branding": yes_no(decisions.branding),
    }


def save_results(path: Path, results: list[SearchResult]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [result_row(result) for result in results]
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def print_result_summary(results: list[SearchResult], budget: int, step: int, top: int) -> None:
    print(f"Combinaciones evaluadas: {len(results):,}".replace(",", "."))
    print(f"Presupuesto: {money(budget)}")
    print(f"Incremento semanal probado: {money(step)}")

    if not results:
        print("No hay combinaciones factibles con estos parametros.")
        return

    best = results[0]
    decisions = best.decisions
    simulation = best.simulation

    print("\nMejor asignacion")
    print(f"- WAW semana 14: {best.week_14_waw:,.0f}".replace(",", "."))
    print(f"- WAW acumulado semanas 1-14: {best.total_waw:,.0f}".replace(",", "."))
    print(f"- Inversion total usada: {money(best.spent)}")
    print(f"- Presupuesto sin usar: {money(best.unspent)}")
    print(f"- Medios pagos: {money(decisions.paid_media_weekly)} / semana")
    print(f"- Activacion en cines: {money(decisions.cinema_activation_weekly)} / semana")
    print(f"- Gift Hours: {yes_no(decisions.gift_hours)}")
    print(f"- Reviews: {yes_no(decisions.reviews)}")
    print(f"- Review Share: {yes_no(decisions.review_share)}")
    print(f"- Branding: {yes_no(decisions.branding)}")
    print(f"- WAW por semana: {week_values(simulation.waw)}")
    print(f"- New watchers por semana: {week_values(simulation.new_watchers)}")
    print(f"- Retained watchers por semana: {week_values(simulation.retained_watchers)}")

    print(f"\nTop {min(top, len(results))}")
    header = (
        "rank | W14 | WAW total | usado | libre | paid/sem | cines/sem | "
        "gift | reviews | share | brand"
    )
    print(header)
    print("-" * len(header))
    for rank, result in enumerate(results[:top], 1):
        d = result.decisions
        print(
            f"{rank:>4} | {result.week_14_waw:>3} | {result.total_waw:>9} | "
            f"{result.spent:>5} | {result.unspent:>5} | "
            f"{d.paid_media_weekly:>8} | {d.cinema_activation_weekly:>9} | "
            f"{yes_no(d.gift_hours):>4} | {yes_no(d.reviews):>7} | "
            f"{yes_no(d.review_share):>5} | {yes_no(d.branding):>5}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "LatamTV quantitative growth model and exhaustive budget allocation search."
        )
    )
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--step", type=int, default=DEFAULT_STEP)
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument(
        "--require-full-budget",
        action="store_true",
        help="Only keep combinations that spend the exact budget.",
    )
    parser.add_argument(
        "--save-all",
        type=Path,
        help="Optional CSV path to save every feasible combination.",
    )
    parser.add_argument(
        "--save-top",
        type=Path,
        help="Optional CSV path to save only the printed top results.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.step <= 0:
        raise ValueError("--step must be greater than zero")
    if args.budget < 0:
        raise ValueError("--budget cannot be negative")
    if args.top <= 0:
        raise ValueError("--top must be greater than zero")

    results = exhaustive_search(
        budget=args.budget,
        step=args.step,
        require_full_budget=args.require_full_budget,
    )
    print_result_summary(results, budget=args.budget, step=args.step, top=args.top)

    if args.save_all:
        save_results(args.save_all, results)
    if args.save_top:
        save_results(args.save_top, results[: args.top])


if __name__ == "__main__":
    main()
