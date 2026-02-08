# Snowflake Cortex AI Agent Development Environment Setup

This document describes how to set up the development environment for the Snowflake Cortex AI agent project.

## Environment Configuration

The project uses a conda environment named `snowflakeCortex` with the following packages installed:

- langchain==0.3.27
- langchain-core==0.3.83
- langchain-community==0.3.31
- langchain-snowflake==0.2.2
- langgraph (latest compatible version)
- snowflake-snowpark-python==1.42.0
- trulens-core==2.5.3
- trulens-apps-langgraph==2.4.2
- trulens-connectors-snowflake
- trulens-dashboard
- trulens-providers-cortex

## Activating the Environment

To activate the conda environment:

```bash
conda activate snowflakeCortex
```

## Running the Project

Once the environment is activated, you can run the Jupyter notebooks in the repository:

```bash
jupyter notebook
```

Then open either:
- `build-and-evaluate-langgraph-agents-with-mcp-tools.ipynb`
- `build-and-evaluate-langgraph-agents-with-mcp-tools-trulens.ipynb`

## Important Notes

- The project requires a Snowflake account with appropriate permissions
- You will need to configure your Snowflake credentials in the notebook
- Make sure to update your account settings according to the instructions in `alter_account_settings.sql`
- Python 3.9 is currently used, though it's approaching EOL (see deprecation warning during import)

## Troubleshooting

If you encounter issues with the virtual environment, ensure you're using the conda environment:

1. Deactivate any other virtual environments
2. Activate the conda environment: `conda activate snowflakeCortex`
3. Verify the correct packages are installed: `pip list | findstr -i "langchain snowflake trulens"`

## Testing the Environment

Run the test script to verify your environment:

```bash
python test_environment.py
```