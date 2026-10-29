// Graph schema v0 (#14). Model: docs/graph-model.md.
// Every node carries a server-generated UUID string in `id`.
// Neo4j Community supports only uniqueness constraints, so `id` is not enforced as present here.

CREATE CONSTRAINT application_id IF NOT EXISTS FOR (n:Application) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT app_version_id IF NOT EXISTS FOR (n:AppVersion) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT window_id IF NOT EXISTS FOR (n:Window) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT element_id IF NOT EXISTS FOR (n:Element) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT repo_object_id IF NOT EXISTS FOR (n:RepoObject) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT test_case_id IF NOT EXISTS FOR (n:TestCase) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT step_id IF NOT EXISTS FOR (n:Step) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT run_id IF NOT EXISTS FOR (n:Run) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT step_result_id IF NOT EXISTS FOR (n:StepResult) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT healing_proposal_id IF NOT EXISTS FOR (n:HealingProposal) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT rule_id IF NOT EXISTS FOR (n:Rule) REQUIRE n.id IS UNIQUE;

// Lookups the first APIs need: applications and repository objects by name,
// elements of one snapshot or by AutomationId, run history by start time.
CREATE INDEX application_name IF NOT EXISTS FOR (n:Application) ON (n.name);
CREATE INDEX repo_object_name IF NOT EXISTS FOR (n:RepoObject) ON (n.name);
CREATE INDEX element_snapshot_id IF NOT EXISTS FOR (n:Element) ON (n.snapshotId);
CREATE INDEX element_automation_id IF NOT EXISTS FOR (n:Element) ON (n.automationId);
CREATE INDEX run_started_at IF NOT EXISTS FOR (n:Run) ON (n.startedAt);
