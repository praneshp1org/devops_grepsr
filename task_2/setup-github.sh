#!/bin/bash

echo "🚀 Setting up GitHub repository for assessment submission..."

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository. Please run 'git init' first."
    exit 1
fi

echo "✅ Git repository detected"

# Check if GitHub CLI is installed
if command -v gh &> /dev/null; then
    echo "✅ GitHub CLI detected"
    
    # Create repository if it doesn't exist
    read -p "Enter GitHub repository name (e.g., microservices-devops-assessment): " REPO_NAME
    
    if [ -n "$REPO_NAME" ]; then
        echo "📦 Creating GitHub repository: $REPO_NAME"
        gh repo create "$REPO_NAME" --public --description "Microservices DevOps Assessment - Docker, Kubernetes, CI/CD"
        
        # Set remote origin
        gh repo set-default "$REPO_NAME"
        
        echo "✅ Repository created successfully"
    fi
else
    echo "⚠️  GitHub CLI not found. Please create repository manually at https://github.com/new"
fi

# Add all files
echo "📁 Adding files to git..."
git add .

# Create initial commit
echo "💾 Creating initial commit..."
git commit -m "Initial commit: Complete microservices DevOps assessment

✅ Docker: Production-grade containerization
✅ Kubernetes: Full deployment manifests with persistence
✅ CI/CD: GitHub Actions with test/build/deploy/rollback
✅ Documentation: Comprehensive setup and troubleshooting guide

Ready for assessment review!"

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "🎉 Repository setup complete!"
echo ""
echo "📋 Next Steps for Assessment:"
echo "1. ✅ Code is ready for review"
echo "2. 🔧 Optional: Configure GitHub Actions secrets for live CI/CD"
echo "3. 📖 Share repository URL with assessors"
echo ""
echo "🔗 Repository URL: $(git remote get-url origin 2>/dev/null || echo 'Manual setup required')"
echo ""
echo "💡 For live CI/CD demo, configure these GitHub secrets:"
echo "   - KUBECONFIG (base64-encoded K8s config)"
echo "   - SLACK_WEBHOOK_URL (optional notifications)"