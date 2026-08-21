from platform_vnext.skills.contracts import GreenSkill, SkillStatus, SkillStep


PYTHON_IMPLEMENTATION = GreenSkill(
    skill_id="GS-PY-001",
    name="Python Implementation",
    version="1.0.0",
    owner="greenz-ai-engineering",
    capability="CODING",
    status=SkillStatus.ACTIVE,
    prerequisites=("task_specification", "writable_workspace", "validation_commands"),
    allowed_toolsets=("READ_SOURCE", "WRITE_WORKSPACE", "RUN_TESTS", "RUN_LINT", "RUN_TYPECHECK"),
    expected_artifacts=("changed_files", "diff", "validation_results"),
    validation_gates=("tests_pass", "diff_valid", "overwrite_policy_pass", "path_policy_pass"),
    evidence_requirements=("changed_files", "validation_results", "diff_summary"),
    procedure=(
        SkillStep("inspect_task", "Understand the bounded task specification."),
        SkillStep("inspect_sources", "Inspect relevant source and interfaces."),
        SkillStep("implement_change", "Implement only the requested change."),
        SkillStep("format", "Run the repository formatter."),
        SkillStep("typecheck", "Run the repository type checker."),
        SkillStep("test", "Run targeted and architecture tests."),
        SkillStep("inspect_diff", "Verify no unrelated or destructive changes occurred."),
        SkillStep("produce_evidence", "Record validation and artifact evidence."),
    ),
)
