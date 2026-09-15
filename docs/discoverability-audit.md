# GitHub discoverability audit

Audit date: 2026-09-15

## What was observable

The public repository showed 1 star, 1 fork, 0 watchers, no published GitHub
release, and 18 commits on the default branch. The owner-provided GitHub traffic
baseline on 2026-09-15 (the rolling 14-day view) showed 0 views, 10 clones by 9
unique cloners, and no referring sites. Its topics already covered the important
broad terms: agent memory, AI agents, Claude Code, Claude Code plugin, coding
assistant, Cursor, developer tools, LLM, and persistent memory.

An exact-name web search did not surface the repository among the leading
results, while many newer general-purpose Claude memory projects did appear.
That makes missing topics an unlikely primary problem. The public README was
also behind the current product: it emphasized a standalone clone and linear
grep workflow, put the plugin later, and did not show the systematic debugging
skill, bundled CLI, ranked retrieval, providers, or verified no-hit behavior.

The owner-provided traffic snapshot could not be refreshed programmatically
because the local GitHub CLI credential had expired. GitHub does not expose a
repository search-term report in the public page, so exact-name web search was
used only as a coarse indexing check.

The project was not visible in Anthropic's official plugin marketplace during
the audit. GitHub's public community profile also had no contribution guide,
security policy, or focused issue forms on the default branch. These are factual
distribution and trust gaps; they do not by themselves explain usage.

## Working diagnosis

1. **The category is broad and crowded.** “AI agent memory” competes with large,
   general memory layers. The product's defensible entry point is narrower:
   recalling a verified fix when a concrete debugging failure appears.
2. **The public page does not prove the loop.** There was no short visual demo,
   reproducible fixture, or recorded transcript showing recall changing the
   investigation.
3. **The fastest install path was not first.** Claude plugin users saw the
   standalone clone and PATH setup before the marketplace commands, even though
   version 0.2.0 bundles its CLI.
4. **Release and trust signals were thin.** There was no GitHub release or
   visible contribution, security, or focused issue-reporting guidance.
5. **External authority is still low.** With one star and one fork, GitHub and
   web search have little third-party evidence that the project answers this
   specific problem. Documentation alone cannot manufacture that evidence.

## Repository changes in this milestone

- Lead the README with “recall verified fixes when debugging,” a before/after
  flow, and a 60-second demo generated from a real fixture transcript.
- Put the three-command Claude Code installation before standalone CLI setup.
- State and test the no-hit/backend-outage continuation behavior.
- Add a dated, sourced comparison with Claude auto memory and adjacent tools.
- Add contribution, security, and focused issue templates.
- Add a correctly sized social-preview image and verify documentation links and
  demo assets in the test suite.

## Prepared GitHub metadata

These values are proposals only; repository settings were not changed.

**Description**

> Recall verified fixes when Claude Code hits a failure—then verify, solve, and
> save the lesson for next time.

**Homepage**

> https://github.com/atazifor/engineering-memlog#readme

**Topics**

Keep the existing relevant topics and prioritize these ten if GitHub's topic
limit requires pruning:

`claude-code`, `claude-code-plugin`, `debugging`, `agent-memory`,
`persistent-memory`, `developer-tools`, `coding-assistant`, `ai-agents`,
`local-first`, `python`

**Social preview**

Upload [`assets/social-preview.png`](../assets/social-preview.png).

## External actions that still require owner approval

- Reauthenticate GitHub CLI and inspect private traffic/referrer data.
- Update the repository description, homepage, topics, and social preview.
- Create the `v0.2.0` tag and GitHub release.
- Submit to marketplaces, directories, newsletters, or curated lists.
- Publish launch posts or contact prospective pilot users.

After launch, review unique visitors, clone conversion, install friction reports,
and successful demo reproductions after 7 and 30 days. Before a wider launch,
complete 3–5 independent plugin install attempts and log and triage every point
of friction. Save a dated traffic baseline at publication and weekly snapshots
for four weeks. Stars alone are not a usefulness metric; confirmed installs and
recalled fixes are better signals.
