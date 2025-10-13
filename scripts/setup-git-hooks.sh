#!/bin/bash

# Git Security Hooks Installation Script
# Installs pre-commit and pre-push hooks to prevent secret leaks

set -e

echo "🔐 Installing Git Security Hooks..."
echo ""

# Ensure .git/hooks directory exists
mkdir -p .git/hooks

# Create pre-commit hook
cat > .git/hooks/pre-commit << 'PRECOMMIT_EOF'
#!/bin/bash

# Pre-commit hook: Prevent committing secrets
echo "🔍 Running security checks..."

# Check if security_manager.py exists
if [ ! -f "orchestration/security_manager.py" ]; then
    echo "⚠️  Warning: security_manager.py not found, skipping secret scan"
    exit 0
fi

# Scan staged files for secrets
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(py|js|json|yaml|yml|sh|env)$' || true)

if [ -n "$STAGED_FILES" ]; then
    echo "📝 Scanning staged files for secrets..."
    
    # Check for .env files
    if echo "$STAGED_FILES" | grep -q '\.env'; then
        echo "❌ ERROR: Attempting to commit .env file!"
        echo "   .env files should NEVER be committed"
        echo "   Add to .gitignore: .env, .env.local, .env.*.local"
        exit 1
    fi
    
    # Check for hardcoded credentials in diff
    if git diff --cached | grep -qiE '(api[_-]?key|token|password|secret)\s*[:=]\s*["\'][^"\']{8,}'; then
        echo "⚠️  WARNING: Possible hardcoded credentials detected!"
        echo "   Review your changes carefully before committing"
        echo ""
        echo "   Common false positives:"
        echo "   - Example code with placeholder values"
        echo "   - Test fixtures with fake credentials"
        echo "   - Documentation with sample values"
        echo ""
        read -p "   Do you want to proceed? (yes/no): " choice
        if [ "$choice" != "yes" ]; then
            echo "❌ Commit aborted"
            exit 1
        fi
    fi
fi

echo "✅ Security checks passed"
exit 0
PRECOMMIT_EOF

# Create pre-push hook
cat > .git/hooks/pre-push << 'PREPUSH_EOF'
#!/bin/bash

# Pre-push hook: Final security validation
echo "🔐 Running pre-push security validation..."

# Check if security_manager.py exists
if [ ! -f "orchestration/security_manager.py" ]; then
    echo "⚠️  Warning: security_manager.py not found, skipping validation"
    exit 0
fi

# Validate environment variables are not hardcoded
if python3 orchestration/security_manager.py --scan 2>&1 | grep -q "Issues found: [1-9]"; then
    echo "⚠️  WARNING: Security scan found potential issues"
    echo "   Run: python3 orchestration/security_manager.py --scan"
    echo ""
    read -p "   Do you want to proceed with push? (yes/no): " choice
    if [ "$choice" != "yes" ]; then
        echo "❌ Push aborted"
        exit 1
    fi
fi

echo "✅ Pre-push validation passed"
exit 0
PREPUSH_EOF

# Make hooks executable
chmod +x .git/hooks/pre-commit
chmod +x .git/hooks/pre-push

echo "✅ Git hooks installed successfully!"
echo ""
echo "📋 Installed hooks:"
echo "   • pre-commit: Prevents committing secrets and .env files"
echo "   • pre-push: Validates no hardcoded credentials before push"
echo ""
echo "🔧 To bypass hooks (use with caution):"
echo "   git commit --no-verify"
echo "   git push --no-verify"
echo ""
echo "✨ Git security hooks are now active!"
