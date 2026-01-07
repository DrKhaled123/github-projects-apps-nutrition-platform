-- PostgreSQL Production Schema for DoctorHealthy Platform
-- HIPAA-Compliant Database Design
-- Created: 2025-10-17
-- Version: 1.0

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create custom types for better data integrity
CREATE TYPE user_goal AS ENUM (
    'weight_loss',
    'muscle_gain', 
    'maintenance',
    'endurance',
    'strength',
    'flexibility',
    'rehabilitation'
);

CREATE TYPE activity_level AS ENUM (
    'sedentary',
    'light',
    'moderate',
    'active',
    'very_active'
);

CREATE TYPE gender AS ENUM (
    'male',
    'female',
    'other',
    'prefer_not_to_say'
);

CREATE TYPE metabolic_rate AS ENUM (
    'slow',
    'medium',
    'fast'
);

-- API Keys table with enhanced security
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) UNIQUE NOT NULL,
    key_prefix VARCHAR(10) NOT NULL,
    permissions JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    usage_count BIGINT DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT api_keys_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT api_keys_future_expires CHECK (expires_at IS NULL OR expires_at > created_at),
    CONSTRAINT api_keys_usage_count_non_negative CHECK (usage_count >= 0)
);

-- Enhanced indexes for API keys
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = true;
CREATE INDEX idx_api_keys_expires_at ON api_keys(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_api_keys_permissions_gin ON api_keys USING gin(permissions);
CREATE INDEX idx_api_keys_created_by ON api_keys(created_by);
CREATE INDEX idx_api_keys_last_used ON api_keys(last_used_at DESC) WHERE last_used_at IS NOT NULL;

-- Users table with comprehensive health data
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    age INTEGER,
    weight DECIMAL(5,2), -- kg
    height DECIMAL(5,2), -- cm
    gender gender,
    activity_level activity_level,
    metabolic_rate metabolic_rate,
    goal user_goal,
    food_dislikes TEXT[],
    allergies TEXT[],
    diseases TEXT[],
    medications TEXT[],
    preferred_cuisine VARCHAR(50),
    language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    email_verified BOOLEAN DEFAULT false,
    phone VARCHAR(20),
    date_of_birth DATE,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT users_email_valid CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'),
    CONSTRAINT users_age_reasonable CHECK (age IS NULL OR (age >= 13 AND age <= 120)),
    CONSTRAINT users_weight_reasonable CHECK (weight IS NULL OR (weight > 20 AND weight < 500)),
    CONSTRAINT users_height_reasonable CHECK (height IS NULL OR (height > 50 AND height < 300)),
    CONSTRAINT users_name_not_empty CHECK (length(trim(name)) > 0)
);

-- Optimized indexes for users
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_goal ON users(goal);
CREATE INDEX idx_users_activity_level ON users(activity_level);
CREATE INDEX idx_users_diseases_gin ON users USING gin(diseases);
CREATE INDEX idx_users_allergies_gin ON users USING gin(allergies);
CREATE INDEX idx_users_active ON users(is_active) WHERE is_active = true;
CREATE INDEX idx_users_created_at ON users(created_at DESC);
CREATE INDEX idx_users_name ON users USING gin(to_tsvector('english', name));

-- HIPAA-compliant audit logs table
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID REFERENCES users(id),
    session_id VARCHAR(255),
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL DEFAULT true,
    error_message TEXT,
    error_code VARCHAR(50),
    request_id VARCHAR(255),
    response_time_ms INTEGER,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Optimized indexes for audit logs
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_events_user_id ON audit_events(user_id);
CREATE INDEX idx_audit_events_action ON audit_events(action);
CREATE INDEX idx_audit_events_resource ON audit_events(resource);
CREATE INDEX idx_audit_events_success ON audit_events(success);
CREATE INDEX idx_audit_events_ip_address ON audit_events(ip_address);
CREATE INDEX idx_audit_events_metadata_gin ON audit_events USING gin(metadata);
CREATE INDEX idx_audit_events_session_id ON audit_events(session_id);

-- Partition audit logs by month for performance and retention
CREATE TABLE audit_events_y2024m11 PARTITION OF audit_events
    FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');

-- Nutrition plans table
CREATE TABLE nutrition_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_type VARCHAR(50) NOT NULL,
    duration_weeks INTEGER DEFAULT 1,
    daily_calories INTEGER,
    macros JSONB NOT NULL DEFAULT '{}'::jsonb,
    meals JSONB NOT NULL DEFAULT '[]'::jsonb,
    restrictions TEXT[],
    preferences TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    generated_by VARCHAR(50) DEFAULT 'system',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT nutrition_plans_duration_positive CHECK (duration_weeks > 0),
    CONSTRAINT nutrition_plans_calories_reasonable CHECK (daily_calories IS NULL OR (daily_calories >= 800 AND daily_calories <= 5000))
);

-- Indexes for nutrition plans
CREATE INDEX idx_nutrition_plans_user_id ON nutrition_plans(user_id);
CREATE INDEX idx_nutrition_plans_active ON nutrition_plans(is_active) WHERE is_active = true;
CREATE INDEX idx_nutrition_plans_plan_type ON nutrition_plans(plan_type);
CREATE INDEX idx_nutrition_plans_created_at ON nutrition_plans(created_at DESC);
CREATE INDEX idx_nutrition_plans_restrictions_gin ON nutrition_plans USING gin(restrictions);

-- Workout plans table
CREATE TABLE workout_plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal user_goal NOT NULL,
    workout_type VARCHAR(20) NOT NULL DEFAULT 'gym',
    injuries TEXT[],
    equipment_available TEXT[],
    duration_weeks INTEGER DEFAULT 1,
    exercises JSONB NOT NULL DEFAULT '[]'::jsonb,
    difficulty_level VARCHAR(20) DEFAULT 'beginner',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    generated_by VARCHAR(50) DEFAULT 'system',
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT workout_plans_duration_positive CHECK (duration_weeks > 0),
    CONSTRAINT workout_plans_valid_type CHECK (workout_type IN ('gym', 'home', 'outdoor', 'pool')),
    CONSTRAINT workout_plans_valid_difficulty CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced'))
);

-- Indexes for workout plans
CREATE INDEX idx_workout_plans_user_id ON workout_plans(user_id);
CREATE INDEX idx_workout_plans_goal ON workout_plans(goal);
CREATE INDEX idx_workout_plans_active ON workout_plans(is_active) WHERE is_active = true;
CREATE INDEX idx_workout_plans_workout_type ON workout_plans(workout_type);
CREATE INDEX idx_workout_plans_created_at ON workout_plans(created_at DESC);
CREATE INDEX idx_workout_plans_injuries_gin ON workout_plans USING gin(injuries);

-- Recipes table
CREATE TABLE recipes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cuisine VARCHAR(50),
    meal_type VARCHAR(50), -- breakfast, lunch, dinner, snack
    difficulty VARCHAR(20) DEFAULT 'easy',
    prep_time_minutes INTEGER,
    cook_time_minutes INTEGER,
    servings INTEGER DEFAULT 1,
    calories_per_serving INTEGER,
    ingredients JSONB NOT NULL DEFAULT '[]'::jsonb,
    instructions JSONB NOT NULL DEFAULT '[]'::jsonb,
    nutrition_info JSONB DEFAULT '{}'::jsonb,
    dietary_tags TEXT[],
    allergens TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT recipes_name_not_empty CHECK (length(trim(name)) > 0),
    CONSTRAINT recipes_prep_time_positive CHECK (prep_time_minutes IS NULL OR prep_time_minutes >= 0),
    CONSTRAINT recipes_cook_time_positive CHECK (cook_time_minutes IS NULL OR cook_time_minutes >= 0),
    CONSTRAINT recipes_servings_positive CHECK (servings > 0),
    CONSTRAINT recipes_calories_reasonable CHECK (calories_per_serving IS NULL OR (calories_per_serving >= 0 AND calories_per_serving <= 2000))
);

-- Indexes for recipes
CREATE INDEX idx_recipes_name ON recipes USING gin(to_tsvector('english', name));
CREATE INDEX idx_recipes_cuisine ON recipes(cuisine);
CREATE INDEX idx_recipes_meal_type ON recipes(meal_type);
CREATE INDEX idx_recipes_difficulty ON recipes(difficulty);
CREATE INDEX idx_recipes_active ON recipes(is_active) WHERE is_active = true;
CREATE INDEX idx_recipes_dietary_tags_gin ON recipes USING gin(dietary_tags);
CREATE INDEX idx_recipes_allergens_gin ON recipes USING gin(allergens);
CREATE INDEX idx_recipes_calories ON recipes(calories_per_serving);

-- User sessions table for authentication tracking
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    refresh_token VARCHAR(255) UNIQUE,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Constraints
    CONSTRAINT user_sessions_expires_future CHECK (expires_at > created_at),
    CONSTRAINT user_sessions_token_not_empty CHECK (length(trim(session_token)) > 0)
);

-- Indexes for user sessions
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_user_sessions_refresh_token ON user_sessions(refresh_token);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active) WHERE is_active = true;

-- Create trigger function for updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_api_keys_updated_at BEFORE UPDATE ON api_keys
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_nutrition_plans_updated_at BEFORE UPDATE ON nutrition_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workout_plans_updated_at BEFORE UPDATE ON workout_plans
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_recipes_updated_at BEFORE UPDATE ON recipes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_sessions_updated_at BEFORE UPDATE ON user_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to create monthly partitions for audit logs
CREATE OR REPLACE FUNCTION create_monthly_audit_partition()
RETURNS void AS $$
DECLARE
    start_date date;
    end_date date;
    partition_name text;
BEGIN
    start_date := date_trunc('month', CURRENT_DATE + interval '1 month');
    end_date := start_date + interval '1 month';
    partition_name := 'audit_events_y' || to_char(start_date, 'YYYY') || 'm' || to_char(start_date, 'MM');
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF audit_events FOR VALUES FROM (%L) TO (%L)',
                   partition_name, start_date, end_date);
                   
    -- Create indexes for the new partition
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I(timestamp DESC)', 
                   'idx_' || partition_name || '_timestamp', partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I(user_id)', 
                   'idx_' || partition_name || '_user_id', partition_name);
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old audit logs (HIPAA retention: 7 years)
CREATE OR REPLACE FUNCTION cleanup_old_audit_logs()
RETURNS void AS $$
BEGIN
    DELETE FROM audit_events 
    WHERE timestamp < NOW() - interval '7 years';
END;
$$ LANGUAGE plpgsql;

-- Create view for active users with recent activity
CREATE OR REPLACE VIEW active_users AS
SELECT 
    u.id,
    u.email,
    u.name,
    u.last_login_at,
    COUNT(ae.id) as recent_activity_count
FROM users u
LEFT JOIN audit_events ae ON u.id = ae.user_id 
    AND ae.timestamp > NOW() - interval '7 days'
WHERE u.is_active = true
GROUP BY u.id, u.email, u.name, u.last_login_at
ORDER BY recent_activity_count DESC;

-- Create view for user statistics
CREATE OR REPLACE VIEW user_statistics AS
SELECT 
    COUNT(*) as total_users,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_users,
    COUNT(CASE WHEN last_login_at > NOW() - interval '7 days' THEN 1 END) as users_last_7_days,
    COUNT(CASE WHEN last_login_at > NOW() - interval '30 days' THEN 1 END) as users_last_30_days,
    AVG(age) FILTER (WHERE age IS NOT NULL) as avg_age,
    mode() WITHIN GROUP (ORDER BY goal) as most_common_goal,
    mode() WITHIN GROUP (ORDER BY activity_level) as most_common_activity_level
FROM users;

COMMIT;
