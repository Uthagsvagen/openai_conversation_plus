#!/bin/bash
# Frontend development setup for OpenAI Conversation Plus
# Based on Home Assistant frontend development guide

echo "OpenAI Conversation Plus - Frontend Development Setup"
echo "========================================================"

# Check if the component has frontend files
if [ ! -d "frontend" ]; then
    echo "No frontend directory found. This component may not have custom UI elements."
    echo "If you plan to add frontend components, create a 'frontend' directory first."
    exit 0
fi

# Check for Node.js
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Please install Node.js first."
    echo "Recommended: Use nvm (Node Version Manager)"
    echo "Visit: https://github.com/nvm-sh/nvm"
    exit 1
fi

# Check for yarn
if ! command -v yarn &> /dev/null; then
    echo "Yarn is not installed. Installing yarn..."
    npm install -g yarn
fi

cd frontend

# Install dependencies if package.json exists
if [ -f "package.json" ]; then
    echo "Installing frontend dependencies..."
    yarn install
else
    echo "No package.json found. Creating basic frontend structure..."

    # Create package.json
    cat > package.json << 'EOF'
{
  "name": "extended-openai-conversation-frontend",
  "version": "1.0.0",
  "description": "Frontend for OpenAI Conversation Plus",
  "scripts": {
    "build": "rollup -c",
    "dev": "rollup -c -w",
    "lint": "eslint src/",
    "format": "prettier --write src/"
  },
  "devDependencies": {
    "@rollup/plugin-commonjs": "^25.0.0",
    "@rollup/plugin-node-resolve": "^15.0.0",
    "@rollup/plugin-typescript": "^11.0.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0",
    "rollup": "^4.0.0",
    "rollup-plugin-terser": "^7.0.0",
    "typescript": "^5.0.0",
    "lit": "^3.0.0",
    "@lit/reactive-element": "^2.0.0",
    "custom-card-helpers": "^1.9.0"
  }
}
EOF

    # Create rollup config
    cat > rollup.config.js << 'EOF'
import typescript from '@rollup/plugin-typescript';
import commonjs from '@rollup/plugin-commonjs';
import nodeResolve from '@rollup/plugin-node-resolve';
import { terser } from 'rollup-plugin-terser';

const production = !process.env.ROLLUP_WATCH;

export default {
  input: 'src/index.ts',
  output: {
    file: '../custom_components/openai_conversation_plus/frontend/bundle.js',
    format: 'es',
  },
  plugins: [
    nodeResolve(),
    commonjs(),
    typescript({
      sourceMap: !production,
      inlineSources: !production,
    }),
    production && terser(),
  ],
};
EOF

    # Create src directory
    mkdir -p src

    # Create basic TypeScript config
    cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "es2020",
    "module": "esnext",
    "moduleResolution": "node",
    "experimentalDecorators": true,
    "emitDecoratorMetadata": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "strict": true,
    "noImplicitAny": true,
    "sourceMap": true,
    "jsx": "preserve",
    "allowSyntheticDefaultImports": true
  },
  "include": ["src/**/*.ts"],
  "exclude": ["node_modules"]
}
EOF

    echo "Basic frontend structure created."
    echo "Installing dependencies..."
    yarn install
fi

echo ""
echo "Frontend development setup complete!"
echo ""
echo "Available commands:"
echo "  yarn dev    - Start development server with hot reload"
echo "  yarn build  - Build production bundle"
echo "  yarn lint   - Run ESLint"
echo "  yarn format - Format code with Prettier"
echo ""
echo "To connect to Home Assistant:"
echo "1. Update configuration.yaml:"
echo "   frontend:"
echo "     development_repo: /path/to/openai_conversation_plus"
echo ""
echo "2. Or run standalone development server:"
echo "   yarn dev"
echo ""
echo "For more info, see: https://developers.home-assistant.io/docs/frontend/development"
