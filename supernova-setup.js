// DoctorHealthy1 Supernova Design System Integration
// This script helps integrate Supernova design tokens with your health platform

const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

class DoctorHealthy1SupernovaSetup {
    constructor() {
        this.projectRoot = process.cwd();
        this.designSystemId = 'doctorhealthy1-health-platform'; // You'll get this from Supernova
        this.apiKey = process.env.SUPERNOVA_API_KEY; // Set this in your environment
    }

    // Initialize Supernova for DoctorHealthy1
    async initialize() {
        console.log('🏥 Setting up Supernova for DoctorHealthy1...\n');

        // Check if logged in
        try {
            execSync('npx @supernovaio/cli whoami', { stdio: 'pipe' });
            console.log('✅ Already logged into Supernova');
        } catch (error) {
            console.log('🔑 Please login to Supernova first:');
            console.log('npx @supernovaio/cli login');
            return;
        }

        // Describe available design systems
        console.log('\n📋 Checking available design systems...');
        try {
            const output = execSync('npx @supernovaio/cli describe-workspaces', { encoding: 'utf8' });
            console.log('Available workspaces:', output);
        } catch (error) {
            console.log('No workspaces found. You may need to:');
            console.log('1. Create a design system at https://supernova.io');
            console.log('2. Get your Design System ID from the URL');
            console.log('3. Set SUPERNOVA_API_KEY and SUPERNOVA_DESIGN_SYSTEM_ID');
        }
    }

    // Generate DoctorHealthy1 design tokens
    async generateDesignTokens() {
        console.log('\n🎨 Generating DoctorHealthy1 design tokens...\n');

        // Define health-focused color palette
        const healthTokens = {
            colors: {
                primary: {
                    // Main health brand colors
                    'health-blue': '#0ea5e9',
                    'health-green': '#10b981',
                    'health-warn': '#facc15',
                    'health-text': '#0f172a',
                    'health-muted': '#475569',
                    'health-bg': '#f7fbff'
                },
                semantic: {
                    // Semantic health colors
                    'success': '#10b981',
                    'warning': '#f59e0b',
                    'error': '#ef4444',
                    'info': '#3b82f6',
                    'vital': '#dc2626', // For critical health indicators
                    'stable': '#059669', // For good health metrics
                    'attention': '#d97706' // For warnings
                },
                gradients: {
                    'health-gradient': 'linear-gradient(90deg, #0ea5e9, #10b981)',
                    'warm-gradient': 'radial-gradient(1200px 400px at 50% -100px, rgba(14,165,233,.25), transparent)'
                }
            },
            typography: {
                fontFamily: {
                    'primary': 'Inter, system-ui, -apple-system, sans-serif',
                    'heading': 'Inter, system-ui, sans-serif',
                    'mono': 'JetBrains Mono, Consolas, monospace'
                },
                fontSize: {
                    'xs': '0.75rem',
                    'sm': '0.875rem',
                    'base': '1rem',
                    'lg': '1.125rem',
                    'xl': '1.25rem',
                    '2xl': '1.5rem',
                    '3xl': '1.875rem',
                    '4xl': '2.25rem'
                },
                fontWeight: {
                    'light': '300',
                    'normal': '400',
                    'medium': '500',
                    'semibold': '600',
                    'bold': '700',
                    'extrabold': '800'
                }
            },
            spacing: {
                // Health-focused spacing scale
                'health-xs': '0.25rem',   // 4px - small health indicators
                'health-sm': '0.5rem',    // 8px - compact health metrics
                'health-md': '1rem',      // 16px - standard health cards
                'health-lg': '1.5rem',    // 24px - section spacing
                'health-xl': '2rem',      // 32px - major sections
                'health-2xl': '3rem'      // 48px - page margins
            },
            borders: {
                'health-radius-sm': '0.375rem',  // 6px - small health components
                'health-radius-md': '0.5rem',    // 8px - standard components
                'health-radius-lg': '0.75rem',   // 12px - cards and major elements
                'health-radius-xl': '1rem'       // 16px - large containers
            },
            shadows: {
                'health-sm': '0 1px 2px 0 rgb(0 0 0 / 0.05)',
                'health-md': '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                'health-lg': '0 10px 15px -3px rgb(0 0 0 / 0.1)',
                'health-xl': '0 20px 25px -5px rgb(0 0 0 / 0.1)'
            },
            animations: {
                'pulse-health': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
                'bounce-health': 'bounce 1s infinite',
                'spin-health': 'spin 1s linear infinite'
            }
        };

        // Save design tokens for Supernova
        const tokensPath = path.join(this.projectRoot, 'design-tokens');
        if (!fs.existsSync(tokensPath)) {
            fs.mkdirSync(tokensPath, { recursive: true });
        }

        fs.writeFileSync(
            path.join(tokensPath, 'doctorhealthy1-tokens.json'),
            JSON.stringify(healthTokens, null, 2)
        );

        console.log('✅ Design tokens generated for DoctorHealthy1');
        console.log(`📁 Tokens saved to: ${tokensPath}/doctorhealthy1-tokens.json`);

        return healthTokens;
    }

    // Sync tokens with Supernova (when you have an account)
    async syncWithSupernova() {
        if (!this.apiKey || !this.designSystemId) {
            console.log('\n🔑 To sync with Supernova, you need:');
            console.log('1. SUPERNOVA_API_KEY environment variable');
            console.log('2. SUPERNOVA_DESIGN_SYSTEM_ID from your Supernova workspace');
            console.log('\nExample usage:');
            console.log('SUPERNOVA_API_KEY=your-key SUPERNOVA_DESIGN_SYSTEM_ID=your-id npx @supernovaio/cli sync-tokens');
            return;
        }

        console.log(`\n🚀 Syncing DoctorHealthy1 tokens with Supernova...`);
        console.log(`Design System ID: ${this.designSystemId}`);

        try {
            const command = `SUPERNOVA_API_KEY=${this.apiKey} npx @supernovaio/cli sync-tokens --designSystemId ${this.designSystemId}`;
            const output = execSync(command, { encoding: 'utf8' });
            console.log('✅ Tokens synced successfully!');
            console.log(output);
        } catch (error) {
            console.log('❌ Sync failed:', error.message);
            console.log('\nTroubleshooting:');
            console.log('1. Check your API key is valid');
            console.log('2. Verify design system ID');
            console.log('3. Ensure you have write permissions');
        }
    }

    // Generate CSS custom properties from tokens
    async generateCSSVariables() {
        console.log('\n🎨 Generating CSS custom properties...');

        const tokens = JSON.parse(
            fs.readFileSync(path.join(this.projectRoot, 'design-tokens/doctorhealthy1-tokens.json'), 'utf8')
        );

        let css = `:root {\n`;

        // Colors
        Object.entries(tokens.colors.primary).forEach(([key, value]) => {
            css += `  --${key}: ${value};\n`;
        });

        Object.entries(tokens.colors.semantic).forEach(([key, value]) => {
            css += `  --semantic-${key}: ${value};\n`;
        });

        // Typography
        Object.entries(tokens.typography.fontSize).forEach(([key, value]) => {
            css += `  --text-${key}: ${value};\n`;
        });

        Object.entries(tokens.typography.fontWeight).forEach(([key, value]) => {
            css += `  --font-${key}: ${value};\n`;
        });

        // Spacing
        Object.entries(tokens.spacing).forEach(([key, value]) => {
            css += `  --space-${key}: ${value};\n`;
        });

        // Borders
        Object.entries(tokens.borders).forEach(([key, value]) => {
            css += `  --radius-${key}: ${value};\n`;
        });

        // Shadows
        Object.entries(tokens.shadows).forEach(([key, value]) => {
            css += `  --shadow-${key}: ${value};\n`;
        });

        css += `}\n`;

        const cssPath = path.join(this.projectRoot, 'frontend/css');
        fs.writeFileSync(path.join(cssPath, 'design-system.css'), css);

        console.log(`✅ CSS custom properties generated: ${cssPath}/design-system.css`);
    }

    // Create DoctorHealthy1 brand guidelines
    async createBrandGuidelines() {
        console.log('\n📖 Creating DoctorHealthy1 brand guidelines...');

        const guidelines = {
            name: 'DoctorHealthy1',
            tagline: 'Your Personalized Health Companion',
            mission: 'Making evidence-based health guidance accessible to everyone',
            vision: 'A world where personalized health optimization is available to all',

            colors: {
                primary: {
                    'Health Blue': '#0ea5e9',
                    'Health Green': '#10b981',
                    'Warning Yellow': '#facc15'
                },
                usage: 'Use Health Blue for primary actions, Health Green for success states, Warning Yellow for attention needed'
            },

            typography: {
                primary: 'Inter',
                hierarchy: {
                    'H1': 'Bold, 2.25rem - Page titles and main headings',
                    'H2': 'Semibold, 1.5rem - Section headings',
                    'H3': 'Semibold, 1.25rem - Subsection headings',
                    'Body': 'Regular, 1rem - Regular text',
                    'Caption': 'Regular, 0.875rem - Secondary text'
                }
            },

            components: {
                'Health Cards': 'Rounded corners (12px), subtle shadows, primary color accents',
                'Navigation': 'Sticky header with gradient background',
                'Buttons': 'Rounded (10px), clear hierarchy with primary/secondary styles',
                'Forms': 'Clean, accessible, with clear validation states'
            },

            accessibility: {
                'Color Contrast': 'WCAG AA compliant (4.5:1 ratio minimum)',
                'Focus States': 'Visible focus indicators on all interactive elements',
                'Screen Readers': 'Proper ARIA labels and semantic HTML',
                'Keyboard Navigation': 'Full keyboard accessibility'
            }
        };

        fs.writeFileSync(
            path.join(this.projectRoot, 'BRAND-GUIDELINES.json'),
            JSON.stringify(guidelines, null, 2)
        );

        console.log('✅ Brand guidelines created: BRAND-GUIDELINES.json');
    }

    // Main setup function
    async setup() {
        await this.initialize();
        await this.generateDesignTokens();
        await this.generateCSSVariables();
        await this.createBrandGuidelines();

        console.log('\n🎉 DoctorHealthy1 Supernova setup complete!');
        console.log('\n📋 Next steps:');
        console.log('1. Create a free account at https://supernova.io');
        console.log('2. Create a new design system for DoctorHealthy1');
        console.log('3. Get your API key and Design System ID');
        console.log('4. Set environment variables:');
        console.log('   export SUPERNOVA_API_KEY=your-key');
        console.log('   export SUPERNOVA_DESIGN_SYSTEM_ID=your-id');
        console.log('5. Run: node supernova-setup.js');
        console.log('\n🚀 Your health platform design system will be synchronized!');
    }
}

// CLI Usage
if (require.main === module) {
    const setup = new DoctorHealthy1SupernovaSetup();
    setup.setup().catch(console.error);
}

module.exports = DoctorHealthy1SupernovaSetup;