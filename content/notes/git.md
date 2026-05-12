+++
title = 'Git'
date = 2025-12-04T00:00:00+05:30
draft = false
math = true
+++

## Git

Before we start, here's a link to one of the best free books on Git: [Pro Git Book](https://git-scm.com/book/en/v2)

---

### What is Version Control?

When working on a project, we often need to keep track of changes made to the code. Version control systems help us track and reconcile changes across different versions of our codebase.

Think of your codebase as a tree. Each change you make can create a new branch in the tree. It's up to you to decide if your changes are good enough to become part of the main branch. But why a tree? Because we have a single source of truth (the `main` branch) based on which we can reconcile all changes.

Imagine the source of truth is a single branch called `main`. When you want to work on a new feature, you create a branch from `main`, make your changes in that branch, and once you're done, you can merge the branch back into `main`.

This approach allows us to:
1. Work on multiple features in parallel
2. Enable multiple people to work on the same codebase simultaneously
3. Revert to previous stable states if something goes wrong


[![](https://mermaid.ink/img/pako:eNp1klFvgjAQx78Kub2ia7GINovJBH3zbU8TH6pchQQoqWWZE7_7KjAjyexT737__92lvQscVILA4ahFlTofUVw69rxvNyIrd85otGj2WpSHtHGW2zUKU2uku140wOEf9nq8bHGCX5irqnGiu_1tr18XB1UUmTn12nCoXd1r_aONWm2B-oiNs-4G7chqQLrcyZxztKPKLM_5C1LpS_lI1k_JsidSSob0kYRPSfSUrAYEXPvgWQLc6BpdsCMX4hbC5eaJwaRYYAzcXhOUos5NDHF5tbZKlJ9KFX9OrepjClyK_GSjukqEwSgT9jeLe1ZjmaAOVV0a4JSwtgjwC3wD9xgbU0KCKQ1oQGaUBC6cgU-mbEymJGABmwXEY97VhZ-2LRmziT-n1GfE8zx_TnwXMMmM0ptukdp9uv4C9ee5ZA?type=png)](https://mermaid.live/edit#pako:eNp1klFvgjAQx78Kub2ia7GINovJBH3zbU8TH6pchQQoqWWZE7_7KjAjyexT737__92lvQscVILA4ahFlTofUVw69rxvNyIrd85otGj2WpSHtHGW2zUKU2uku140wOEf9nq8bHGCX5irqnGiu_1tr18XB1UUmTn12nCoXd1r_aONWm2B-oiNs-4G7chqQLrcyZxztKPKLM_5C1LpS_lI1k_JsidSSob0kYRPSfSUrAYEXPvgWQLc6BpdsCMX4hbC5eaJwaRYYAzcXhOUos5NDHF5tbZKlJ9KFX9OrepjClyK_GSjukqEwSgT9jeLe1ZjmaAOVV0a4JSwtgjwC3wD9xgbU0KCKQ1oQGaUBC6cgU-mbEymJGABmwXEY97VhZ-2LRmziT-n1GfE8zx_TnwXMMmM0ptukdp9uv4C9ee5ZA)


### Getting Started

First, download Git from [here](https://git-scm.com/downloads) and install it.

In this guide, we'll cover:

1. Setting up Git credentials
2. Creating a new repository
3. Understanding the staging area and making commits
4. Working with branches
5. Merging branches
6. Working with remote repositories
7. Common Git commands and workflows

#### 1. Setting Up Git Credentials

Before you start using Git, configure your name and email. These will be associated with all your commits.

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

You can verify your configuration with:
```bash
git config --list
```

#### 2. Creating a New Repository

Navigate to the directory where you want to create the repository. You can either:
- Initialize an existing directory as a Git repository
- Create a new directory and then initialize it

```bash
# Option 1: Initialize current directory
git init

# Option 2: Create new directory and initialize
mkdir my-project
cd my-project
git init
```

#### 3. Understanding the Staging Area and Making Commits

Git uses a three-stage workflow:
1. **Working Directory**: Your files as they exist on disk
2. **Staging Area**: Files you've marked to be included in the next commit
3. **Repository**: Committed snapshots of your project

Let's create a file and commit it:

```bash
# Create a new file
echo "Hello, World!" > hello.txt

# Stage the file (add it to the staging area)
git add hello.txt

# Commit the changes with a descriptive message
git commit -m "Add hello.txt file"
```

**Key Commands:**
- `git status` - See which files are modified, staged, or untracked
- `git add <file>` - Stage a specific file
- `git add .` - Stage all changes in the current directory
- `git commit -m "message"` - Commit staged changes with a message

#### 4. Working with Branches

Branches allow you to work on features, experiments, or fixes without affecting the main codebase.

**Create and switch to a new branch:**
```bash
git checkout -b feature1
```

This is equivalent to:
```bash
git branch feature1      # Create the branch
git checkout feature1    # Switch to the branch
```

**Modern alternative (Git 2.23+):**
```bash
git switch -c feature1   # Create and switch
```

**Make changes in the new branch:**
```bash
echo "Hello, World! in feature1" > hello.txt
```

**View all branches:**
```bash
git branch                # List local branches
git branch -a            # List all branches (local and remote)
```

#### 5. Committing Changes to a Branch

```bash
git add hello.txt
git commit -m "Update hello.txt in feature1 branch"
```

#### 6. Merging Branches

Once your feature is complete, merge it back into `main`:

```bash
# Switch back to main branch
git checkout main

# Merge feature1 into main
git merge feature1
```

**Note:** If there are no conflicts, Git will automatically create a merge commit. If conflicts occur, you'll need to resolve them manually.

#### 7. Working with Remote Repositories

Remote repositories allow you to collaborate with others and back up your code.

**Add a remote repository:**

First, create a new repository on a platform like GitHub, GitLab, or Bitbucket. Then copy the repository URL and add it as a remote:

```bash
git remote add origin <remote-repository-URL>
```

**View remote repositories:**
```bash
git remote -v              # List all remotes with URLs
```

**Update remote URL (if needed):**
```bash
git remote set-url origin <new-URL>
```

#### 8. Pushing Changes to Remote

Push your local commits to the remote repository:

```bash
git push -u origin main
```

The `-u` flag sets up tracking, so future pushes can be done with just `git push`.

**Push to a specific branch:**
```bash
git push origin feature1
```

#### 9. Pulling Changes from Remote

`git pull` fetches changes from the remote and merges them into your current branch:

```bash
git pull origin main
```

**Note:** `git pull` is equivalent to `git fetch` followed by `git merge`.

#### 10. Fetching Changes from Remote

`git fetch` downloads changes from the remote without merging them:

```bash
git fetch origin
```

This is useful when you want to see what changes exist on the remote before merging them. After fetching, you can review changes with:
```bash
git log origin/main..main    # See commits on remote
git diff origin/main          # See differences
```

---

### Additional Useful Commands

#### Viewing History and Changes

```bash
git log                      # View commit history
git log --oneline            # Compact one-line view
git log --graph --oneline    # Visual branch history
git diff                     # See unstaged changes
git diff --staged            # See staged changes
git show <commit-hash>       # Show details of a specific commit
```

#### Undoing Changes

```bash
git restore <file>           # Discard changes in working directory
git restore --staged <file>  # Unstage a file
git reset HEAD~1             # Undo last commit (keeps changes)
git reset --hard HEAD~1      # Undo last commit (discards changes) - use with caution!
```

#### Working with .gitignore

Create a `.gitignore` file to exclude files from version control:

```bash
# Example .gitignore
node_modules/
*.log
.env
.DS_Store
```

#### Cloning a Repository

To get a copy of an existing repository:

```bash
git clone <repository-URL>
```

This creates a new directory with the repository name and downloads all files and history.

---

### Common Workflows

**Typical workflow:**
1. `git pull` - Get latest changes
2. `git checkout -b feature-name` - Create feature branch
3. Make changes and `git add` files
4. `git commit -m "message"` - Commit changes
5. `git push origin feature-name` - Push to remote
6. Create pull/merge request on platform
7. After review, merge to main
8. `git checkout main && git pull` - Update local main

---

### Tips and Best Practices

1. **Write clear commit messages**: Describe what and why, not how
2. **Commit often**: Small, logical commits are easier to review and revert
3. **Pull before push**: Always pull latest changes before pushing
4. **Use branches**: Keep main stable, work on features in branches
5. **Review before merging**: Check your changes with `git diff` and `git status`

