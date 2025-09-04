#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to print colored output
print_step() {
    echo -e "${BLUE}[STEP $1]${NC} ${CYAN}$2${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to get changed files for commit message
get_changed_files() {
    local repo_path=$1
    local changed_files=$(cd "$repo_path" && git status --porcelain | head -10)
    
    if [ -z "$changed_files" ]; then
        echo "no changes"
        return
    fi
    
    # Extract file names and limit to first 5
    local file_names=$(echo "$changed_files" | awk '{print $2}' | head -5 | tr '\n' ', ' | sed 's/, $//')
    
    if [ $(echo "$changed_files" | wc -l) -gt 5 ]; then
        file_names="$file_names..."
    fi
    
    echo "$file_names"
}

# Function to handle git operations
git_commit_and_push() {
    local repo_path=$1
    local repo_name=$2
    
    cd "$repo_path" || { print_error "Failed to cd to $repo_path"; exit 1; }
    
    # Check if there are changes to commit
    if git diff --quiet && git diff --staged --quiet; then
        print_warning "No changes to commit in $repo_name"
        return
    fi
    
    # Get changed files for commit message
    local changed_files=$(get_changed_files "$repo_path")
    local commit_msg="blog update $(date +%Y-%m-%d) - $changed_files"
    
    print_step "GIT-$repo_name" "Adding changes..."
    git add . || { print_error "Failed to add files in $repo_name"; exit 1; }
    
    print_step "GIT-$repo_name" "Committing changes..."
    echo -e "${PURPLE}Commit message: $commit_msg${NC}"
    git commit -m "$commit_msg" || { print_error "Failed to commit in $repo_name"; exit 1; }
    
    print_step "GIT-$repo_name" "Pushing changes..."
    git push || { print_error "Failed to push in $repo_name"; exit 1; }
    
    print_success "Successfully updated $repo_name repository"
}

# Main script
echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════╗"
echo "║        🚀 Hugo Blog Build & Deploy           ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"

print_step "1" "Building the Hugo site..."
if hugo; then
    print_success "Site built successfully"
else
    print_error "Hugo build failed"
    exit 1
fi

# Handle main repository
print_step "2-4" "Processing main repository..."
git_commit_and_push "." "MAIN"

# Copy public folder to bear repository
print_step "5" "Copying public folder to bear repository..."
if cp -r public/* ../bear/; then
    print_success "Files copied successfully"
else
    print_error "Failed to copy files to bear repository"
    exit 1
fi

# Handle bear repository
print_step "6-9" "Processing bear repository..."
git_commit_and_push "../bear" "BEAR"

echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════╗"
echo "║              🎉 Deployment Complete!         ║"
echo "╚══════════════════════════════════════════════╝"
echo -e "${NC}"
print_success "All operations completed successfully"