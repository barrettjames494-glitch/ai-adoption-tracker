AI Tool Adoption Tracker

I'm James, a data and analytics consultant. Most of my recent work has been helping organisations roll out AI tools and report on how they're landing. One question keeps coming up: which tools are actually gaining traction, and which are quietly stalling?

I built this project to answer that question with public data, and to practise writing the kind of production-style Python pipeline I'd want behind any adoption report I put in front of senior stakeholders.

It tracks ten popular open-source AI tools (Ollama, LangChain, vLLM, the OpenAI and Anthropic SDKs and others), pulls their activity from the GitHub API, checks the data is trustworthy, and turns it into a short report with plain-English takeaways.

How it works
config/tools.yaml ──► extract ──► transform ──► validate ──► metrics ──► report.html
   (10 AI tools)     GitHub API   star schema   17 checks    KPIs +     + CSVs for
                     retries,     (dim + 3      errors stop  momentum    Power BI
                     rate limits   facts)       the run      score

There are five steps, each in its own module so it can be tested on its own:

Extract (extract.py) calls the GitHub API with authentication, pagination and retries. If one repository fails, the rest still run and the failure is logged, because one bad source shouldn't sink the whole report.
Transform (transform.py) reshapes the raw JSON into a small star schema: one tool table and three fact tables (snapshots, weekly commits, releases). It's the same shape I'd load into Power BI.
Validate (validate.py) runs 17 data quality checks: missing columns, nulls, negative counts, duplicates, orphaned rows and stale repositories. Serious problems stop the run, so a misleading report never gets produced. Every result is saved for audit.
Metrics (metrics.py) works out the adoption measures below and writes a few headline insights in plain English.
Report (report.py) builds a single HTML page with charts, a scorecard and a data quality summary that anyone can open.
Running it
bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Try it offline first, using synthetic sample data (no token needed)
PYTHONPATH=src python -m tracker.pipeline --offline

# Then with live GitHub data (a token raises the limit from 60 to 5,000 requests an hour)
export GITHUB_TOKEN=ghp_your_token   # Windows PowerShell: $env:GITHUB_TOKEN="ghp_..."
PYTHONPATH=src python -m tracker.pipeline

On Windows PowerShell, set $env:PYTHONPATH="src" instead of the PYTHONPATH=src prefix.

Everything lands in output/: the report, the metrics, the data quality log and the four model tables as CSVs.

What it measures

Commits (last 12 weeks) How much work is going into the tool right now.

Growth % Commits in the last 12 weeks compared with the 12 weeks before. Tells me whether a project is speeding up or slowing down.

Releases (last 90 days) How often improvements actually reach users.

Days between releases The typical gap between releases. A steady rhythm suggests predictable delivery.

Forks per 100 stars Stars are bookmarks; forks mean people are building on the tool. A higher ratio means deeper engagement.

Issues per 1,000 stars Open issues relative to popularity. A rough measure of support load and risk.

Momentum score (0–100) One figure that blends the measures above so the tools can be compared at a glance:

Growth: 35%
Recent commit volume: 25%
Release frequency: 20%
Fork ratio: 20%

The weights are my own judgement call. They're easy to change in metrics.py.


Testing
- bash
pytest -q

GitHub Actions runs the tests and an offline end-to-end run on every pull request, so nothing gets merged without passing.

What I learned, and what's next
Percentages can mislead. In my first live run, one SDK showed +537% commit growth, enough to push it into the top three. It turned out to be a small number of commits jumping to a slightly bigger one, not a six-fold rise in adoption. Spotting that is the reason I'm adding a minimum-activity threshold to the growth metric.
GitHub activity is only a proxy. It shows how actively a tool is being built, not how widely it's used inside companies. PyPI download figures would be a good second source.
One run is a snapshot. Scheduling daily runs and keeping the history would show proper trends over time.
WIP: a Power BI template on top of the CSVs, scheduled runs through GitHub Actions, and an alert when a tool's momentum drops sharply.