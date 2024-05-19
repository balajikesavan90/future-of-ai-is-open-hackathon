# Contributing to Arctic Analytics

First off, thank you for considering contributing to Arctic Analytics. It's people like you that make Arctic Analytics such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, make sure to check our [issues](https://github.com/balajikesavan90/future-of-ai-is-open-hackathon/issues) if there's something similar to what you have in mind. If there isn't, feel free to open a new issue!

## Fork & create a branch

If this is something you think you can fix, then fork Arctic Analytics and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```bash
git checkout -b 325-<descriptive name>
```

## Implement your fix or feature
At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first 😸

## Get the code
```bash
# Clone your fork of the repo into the current directory
git clone https://github.com/<your-username>/future-of-ai-is-open-hackathon.git

# Navigate to the newly cloned directory
cd future-of-ai-is-open-hackathon

# Assign the original repo to a remote called "upstream"
git remote add upstream https://github.com/balajikesavan90/future-of-ai-is-open-hackathon.git

## Create a new branch
git checkout -b <my-branch-name>
```

## Make your changes
Apply the fix or make the enhancement you want to perform


## Create a pull request
A pull request (PR) lets us review the changes you've made and decide if we want to include them in the project.

## Submitting your changes
Once your changes and tests are complete, you can commit your changes:

```bash
# Add changes to git
git add .

# Commit your changes
git commit -m "Add a brief description of your change"
```
Push your branch to your fork:


```bash
# Push the branch
git push origin <my-branch-name>
```
Then go to the GitHub page of the original Arctic Analytics repository and you'll see your new changes proposed. Hit the "Compare & pull request" button on the page to create a new pull request.


## Keeping your Pull Request updated
If a maintainer asks you to "rebase" your PR, they're saying that a lot of code has changed, and that you need to update your branch so it's easier to merge.

To update your branch:

```bash
# Fetch upstream master and merge with your repo's master branch
git fetch upstream
git rebase upstream/master
# If there were any merge conflicts, resolve them
# Push your updated code
git push origin <my-branch-name>
```

## Thank you for your contribution!
