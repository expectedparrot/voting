# Recipes

Worked patterns for using `voting` in a company or organization. The common
thread: any group choosing among options, where the decision should be
transparent and the counting rule should be chosen on purpose — not inherited
from whichever spreadsheet was handy.

## 1. Roadmap / feature prioritization

Dot-voting in a spreadsheet is plurality voting chosen by default. Collect
rankings instead, then check whether the "winner" survives a change of rule.

```bash
voting init q3_roadmap && cd q3_roadmap
voting election add roadmap "Q3 roadmap priorities" --ballot-type ranked
voting option import --from features.json --election roadmap
voting voter add alice "Alice" && voting voter add bob "Bob"
voting election open roadmap
voting ballot rank roadmap alice sso_login audit_log dark_mode
voting ballot rank roadmap bob audit_log sso_login dark_mode
voting count compare roadmap
voting plot methods --election roadmap
```

**What to look at:** if the methods-comparison grid has a solid top row, the
priority is robust — ship it. If methods disagree, support is fragmented and
the item deserves discussion, not a tally. That disagreement is the finding.

## 2. Hiring or promotion panels

Ranked ballots from each interviewer, counted head-to-head, with explicit
role weights instead of implicit loudest-voice weighting.

```bash
voting election add backend_role "Backend hire" --ballot-type ranked
voting voter add hm "Hiring manager" --weight 2.0
voting voter add ic1 "Panelist 1"
voting ballot rank backend_role hm candidate_b candidate_a candidate_c
voting ballot rank backend_role ic1 candidate_a candidate_b candidate_c
voting count run backend_role --method schulze
voting plot pairwise <result_id>
```

**What to look at:** the pairwise plot shows exactly which head-to-head
comparisons were close. And note what `--method simple_majority` does when no
candidate has majority support: it reports no winner rather than fabricating
one — often the most useful answer a panel can get.

## 3. Customer or employee preference surveys (Humanize)

Publish a hosted ranking survey — pricing-tier names, package designs, next
year's benefit options — email unique links, and analyze the responses.

```bash
voting election add benefits "2027 benefits options" --ballot-type ranked
voting option import --from benefit_options.json --election benefits
voting voter set-trait alice email '"alice@example.com"'
voting survey humanize benefits --email-trait email
voting survey publish benefits
voting survey email benefits --name "Benefits preferences"
voting survey responses benefits
voting ballot import --election benefits \
  --from-results .voting/output/humanize_responses_benefits.ep --register-voters
voting plot ranks benefits
```

**What to look at:** the rank-distribution plot separates "broadly liked"
from "polarizing" in a way a mean score cannot — a long pale tail means some
respondents put that option last, even if its average looks fine.

## 4. AI-persona pretesting

Pilot a preference question against synthetic personas before spending real
respondent budget — or compare the AI panel's rankings to the human panel's
as a study in itself.

```bash
voting voter add p1 "IT manager persona"
voting voter set-trait p1 persona '"Budget-conscious IT manager at a 200-person company"'
voting survey generate pricing --model gpt-5.5 --service openai
ep run --jobs .voting/output/survey_pricing.jobs.ep \
    --output .voting/output/survey_pricing.results.ep
voting ballot import --election pricing \
  --from-results .voting/output/survey_pricing.results.ep
voting count compare pricing
```

`voting` builds the job; `ep run` executes the model calls externally.

## 5. Budget allocation

"Distribute 100 points across these initiatives" maps directly to allocated
ballots and cumulative counting.

```bash
voting election add budget "Team budget split" --ballot-type allocated
voting ballot allocate budget alice infra=40 tooling=35 docs=25
voting ballot allocate budget bob infra=20 tooling=50 docs=30
voting count run budget --method cumulative
voting plot scores <result_id>
```

## Delegating the loop to an agent

Every command emits a JSON envelope and `voting next` always knows the next
valid step, so the whole loop is delegable: "survey the team on these five
options and tell me whether the winner is method-robust" is a task a coding
agent can run end-to-end with this CLI. Point it at `voting agent-bootstrap`
to start.

## Next Steps

- `voting docs show voting-methods` — choosing a counting rule on purpose
- `voting docs show humanize` — the hosted-survey path in full
- `voting docs show workflow` — phase-by-phase reference
