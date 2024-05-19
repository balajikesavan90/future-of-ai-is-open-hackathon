# Arctic Analytics

Arctic Analytics is a powerful tool that can answer questions about your data, build charts and graphs from your data, and help document and debug your codebase. Arctic Analytics does not get access to your dataset.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

What things you need to install the software and how to install them:

- Python 3.10.14
- pip (Python Package Installer)

### Installation

A step by step series of examples that tell you how to get a development environment running:

```bash
# Clone the repository
git clone https://github.com/balajikesavan90/future-of-ai-is-open-hackathon.git

# Change directory
cd future-of-ai-is-open-hackathon

# Install requirements
pip install -r requirements.txt
```

### Setting up secrets

create a secrets.toml and place it in the .streamlit folder. You need to set up 2 keys

- ENV: set this to dev
- REPLICATE_API_TOKEN: Create a replicate account and add your API key here.


### Running the app

```bash
# Run the app
streamlit run app.py
```

### Contributing

I welcome contributions to Arctic Analytics! Here's how you can help:

- Check out our open issues and pick one you'd like to work on.
- Fork the project, make your changes, and submit a pull request.
- Make sure your changes are well-documented.
- Respect the code style and indentation.

Please read CONTRIBUTING.md for details on our code of conduct, and the process for submitting pull requests to us.

### License
This project is licensed under the MIT License - see the LICENSE.md file for details.