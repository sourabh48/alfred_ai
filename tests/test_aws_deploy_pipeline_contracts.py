from pathlib import Path

from django.test import SimpleTestCase


REPO_ROOT = Path(__file__).resolve().parents[1]


class AwsDeployPipelineContractTests(SimpleTestCase):
    def test_github_actions_deploy_workflow_runs_ec2_pull_deploy(self):
        workflow = (REPO_ROOT / ".github" / "workflows" / "aws-deploy.yml").read_text(encoding="utf-8")

        self.assertIn("name: AWS Pull Deploy", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("- main", workflow)
        self.assertIn("- master", workflow)
        self.assertIn("id-token: write", workflow)
        self.assertIn("aws-actions/configure-aws-credentials@v6.2.3", workflow)
        self.assertIn("secrets.AWS_GITHUB_OIDC_ROLE_ARN", workflow)
        self.assertIn("secrets.AWS_EC2_INSTANCE_ID", workflow)
        self.assertIn("aws ssm send-command", workflow)
        self.assertIn("AWS-RunShellScript", workflow)
        self.assertIn("timeout-minutes: 45", workflow)
        self.assertIn('"executionTimeout": ["2700"]', workflow)
        self.assertIn("for attempt in $(seq 1 270)", workflow)
        self.assertIn("https://github.com/${GITHUB_REPOSITORY}.git", workflow)
        self.assertIn('ALFRED_COMMIT_SHA="${GITHUB_SHA}"', workflow)
        self.assertIn('"ALFRED_RUN_READINESS_PROBE": "true"', workflow)
        self.assertIn('"ALFRED_REQUIRE_READINESS": "true"', workflow)
        self.assertIn("/health/live/", workflow)
        self.assertIn("/health/ready/", workflow)
        self.assertIn("scripts/deploy_aws_pull.sh", workflow)
        self.assertIn("/etc/alfred/alfred.env", workflow)
        self.assertNotIn("secrets.AWS_EC2_SSH_KEY", workflow)
        self.assertNotIn("ssh-keyscan", workflow)
        self.assertNotIn("git@github.com:${GITHUB_REPOSITORY}.git", workflow)

    def test_ec2_deploy_script_pulls_exact_commit_and_runs_django_checks(self):
        script = (REPO_ROOT / "scripts" / "deploy_aws_pull.sh").read_text(encoding="utf-8")

        self.assertIn("git clone --branch", script)
        self.assertIn("git fetch origin", script)
        self.assertIn("git checkout --detach \"$COMMIT_SHA\"", script)
        self.assertIn("git pull --ff-only", script)
        self.assertIn('export HOME="${HOME:-/root}"', script)
        self.assertIn("git config --global --add safe.directory \"$DEPLOY_DIR\"", script)
        self.assertIn("has uncommitted changes", script)
        self.assertNotIn("git reset --hard", script)
        self.assertIn("docker compose -f", script)
        self.assertIn("build --pull", script)
        self.assertIn("up -d --remove-orphans", script)
        self.assertIn("python manage.py check", script)
        self.assertIn("python manage.py makemigrations --check --dry-run", script)
        self.assertIn("/health/live/", script)
        self.assertIn("/health/ready/", script)
        self.assertIn('RUN_READINESS_PROBE="${ALFRED_RUN_READINESS_PROBE:-true}"', script)
        self.assertIn('REQUIRE_READINESS="${ALFRED_REQUIRE_READINESS:-true}"', script)
        self.assertIn("run_production_readiness_probe.py", script)

    def test_aws_compose_uses_external_runtime_env_and_separate_processes(self):
        compose = (REPO_ROOT / "docker-compose.aws.yml").read_text(encoding="utf-8")

        self.assertIn("web:", compose)
        self.assertIn("worker:", compose)
        self.assertIn("beat:", compose)
        self.assertIn("${ALFRED_RUNTIME_ENV_FILE:-.env}", compose)
        self.assertIn("gunicorn alfred_ai.wsgi:application", compose)
        self.assertIn("celery -A alfred_ai worker", compose)
        self.assertIn("celery -A alfred_ai beat", compose)
        self.assertNotIn("postgres:", compose)
        self.assertNotIn("redis:", compose)

    def test_pipeline_docs_keep_delivery_separate_from_production_readiness(self):
        docs = (REPO_ROOT / "docs" / "AWS_DEPLOY_PIPELINE.md").read_text(encoding="utf-8")
        aws_docs = (REPO_ROOT / "docs" / "AWS_DEPLOYMENT.md").read_text(encoding="utf-8")
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("EC2 host pulls the requested commit from GitHub", docs)
        self.assertIn("GitHub OIDC", docs)
        self.assertIn("AWS Systems Manager", docs)
        self.assertIn("/etc/alfred/alfred.env", docs)
        self.assertIn("Do not put production secrets in the repository", docs)
        self.assertIn("Deployment Readiness separate from successful deploys", docs)
        self.assertIn("AWS Pull Deployment Pipeline", aws_docs)
        self.assertNotIn("read-only Deploy Key", docs)
        self.assertNotIn("GitHub Actions SSH secrets", aws_docs)
        self.assertIn("docker-compose.aws.yml", readme)
        self.assertIn("aws-deploy.yml", readme)
