-- Test Database Initialization Script
-- This script sets up the database schema for testing

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create test user table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    plan_type VARCHAR(50) DEFAULT 'free'
);

-- Create API keys table
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    key_name VARCHAR(255) NOT NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    rate_limit INTEGER DEFAULT 100
);

-- Create nutrition plans table
CREATE TABLE IF NOT EXISTS nutrition_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(255) NOT NULL,
    plan_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create workout plans table
CREATE TABLE IF NOT EXISTS workout_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    plan_name VARCHAR(255) NOT NULL,
    plan_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create recipes table
CREATE TABLE IF NOT EXISTS recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    ingredients JSONB NOT NULL,
    instructions TEXT,
    nutrition_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Insert test data
-- Test user
INSERT INTO users (email, password_hash, plan_type) VALUES 
('test@example.com', 'hashed_password_test', 'free'),
('premium@example.com', 'hashed_password_premium', 'premium')
ON CONFLICT (email) DO NOTHING;

-- Test API keys
INSERT INTO api_keys (user_id, key_name, api_key, rate_limit) 
SELECT u.id, 'test-key-' || u.email, 'test-api-key-' || u.email, 100 
FROM users u 
WHERE u.email IN ('test@example.com', 'premium@example.com')
ON CONFLICT (api_key) DO NOTHING;

-- Test recipes
INSERT INTO recipes (name, description, ingredients, instructions, nutrition_info) VALUES 
('Protein Bowl', 'High protein bowl for athletes', 
 '{"protein": "30g", "carbs": "45g", "fat": "15g"}'::jsonb,
 'Mix all ingredients together. Serve fresh.',
 '{"calories": 350, "protein": 30, "carbs": 45, "fat": 15}'::jsonb
),
('Green Smoothie', 'Nutrient-dense green smoothie',
 '{"greens": "2 cups", "protein": "1 scoop", "fruit": "1 banana"}'::jsonb,
 'Blend all ingredients until smooth.',
 '{"calories": 280, "protein": 25, "carbs": 35, "fat": 8}'::jsonb
)
ON CONFLICT DO NOTHING;

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_key ON api_keys(api_key);
CREATE INDEX IF NOT EXISTS idx_nutrition_plans_user_id ON nutrition_plans(user_id);
CREATE INDEX IF NOT EXISTS idx_workout_plans_user_id ON workout_plans(user_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_nutrition_plans_updated_at BEFORE UPDATE ON nutrition_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workout_plans_updated_at BEFORE UPDATE ON workout_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Grant permissions to test user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO test_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO test_user;

-- Test data verification
DO $$
DECLARE
    user_count INTEGER;
    api_key_count INTEGER;
    recipe_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO user_count FROM users;
    SELECT COUNT(*) INTO api_key_count FROM api_keys;
    SELECT COUNT(*) INTO recipe_count FROM recipes;
    
    RAISE NOTICE 'Test database initialized successfully';
    RAISE NOTICE 'Users: %, API Keys: %, Recipes: %', user_count, api_key_count, recipe_count;
END $$;
