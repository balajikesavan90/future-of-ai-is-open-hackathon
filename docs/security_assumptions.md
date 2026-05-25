# Security Assumptions

Arctic Analytics assumes a trusted local operator running the application in a controlled development or research environment.

## Assumptions

- Users review generated code and outputs before relying on them.
- Uploaded datasets are appropriate for the local environment where the app is running.
- API keys and secrets are managed outside the repository and are not committed.
- The Python environment and installed dependencies are trusted by the operator.
- Network and filesystem controls, if needed, are provided outside Arctic Analytics.

## Non-Assumptions

- The execution layer is isolated from the host OS.
- The timeout enforces memory or CPU quotas.
- The trace export is a durable audit record.
- Model output is correct, safe, or complete without review.
- The application provides governance, policy enforcement, or access control.
