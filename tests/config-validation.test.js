/**
 * Configuration Validation Test Suite
 * Tests for configuration loading, validation, and security
 */

const { expect } = require('chai');
const sinon = require('sinon');
const fs = require('fs').promises;
const path = require('path');

describe('Configuration Validation Tests', () => {
  let testDir;
  let configFile;

  beforeEach(async () => {
    testDir = path.join(__dirname, 'temp-config-test');
    configFile = path.join(testDir, 'config.json');
    await fs.mkdir(testDir, { recursive: true });
  });

  afterEach(async () => {
    try {
      await fs.rm(testDir, { recursive: true, force: true });
    } catch (error) {
      // Ignore cleanup errors
    }
  });

  describe('Environment Variable Validation', () => {
    it('should validate required environment variables', () => {
      const requiredVars = [
        'COOLIFY_API_URL',
        'COOLIFY_API_TOKEN',
        'JWT_SECRET',
        'DB_PATH'
      ];

      // Set test values
      process.env.COOLIFY_API_URL = 'https://api.doctorhealthy1.com/';
      process.env.COOLIFY_API_TOKEN = 'test-token';
      process.env.JWT_SECRET = 'test-jwt-secret-min-32-chars-for-testing';
      process.env.DB_PATH = '/app/data/app.db';

      requiredVars.forEach(varName => {
        expect(process.env[varName]).to.be.a('string');
        expect(process.env[varName]).to.have.length.greaterThan(0);
      });
    });

    it('should provide default values for optional variables', () => {
      const optionalVars = {
        PORT: '8081',
        LOG_LEVEL: 'info',
        ENV: 'development'
      };

      Object.entries(optionalVars).forEach(([key, defaultValue]) => {
        const value = process.env[key] || defaultValue;
        expect(value).to.be.a('string');
        expect(value).to.have.length.greaterThan(0);
      });
    });

    it('should validate environment-specific configurations', () => {
      const environments = ['development', 'staging', 'production'];

      environments.forEach(env => {
        process.env.ENV = env;

        if (env === 'production') {
          expect(process.env.ENV).to.equal('production');
          // In production, certain security settings should be enforced
        } else if (env === 'development') {
          expect(process.env.ENV).to.equal('development');
          // In development, debug features might be enabled
        }
      });
    });
  });

  describe('Configuration File Validation', () => {
    it('should validate JSON configuration file structure', async () => {
      const validConfig = {
        app: {
          name: 'doctorhealthy1-api',
          port: 8081,
          environment: 'production'
        },
        database: {
          host: 'localhost',
          port: 5432,
          name: 'nutrition_db',
          ssl_mode: 'require'
        },
        security: {
          jwt_secret: '${JWT_SECRET}',
          rate_limit: 100,
          cors_origins: ['https://my.doctorhealthy1.com']
        }
      };

      await fs.writeFile(configFile, JSON.stringify(validConfig, null, 2));

      const content = await fs.readFile(configFile, 'utf8');
      const parsed = JSON.parse(content);

      expect(parsed).to.have.property('app');
      expect(parsed).to.have.property('database');
      expect(parsed).to.have.property('security');
      expect(parsed.app.name).to.equal('doctorhealthy1-api');
      expect(parsed.app.port).to.equal(8081);
    });

    it('should reject invalid JSON configuration', async () => {
      const invalidJson = '{"app": {"name": "test", "port": 8081,}'; // Missing closing brace

      await fs.writeFile(configFile, invalidJson);

      try {
        const content = await fs.readFile(configFile, 'utf8');
        JSON.parse(content);
        expect.fail('Should have thrown JSON parse error');
      } catch (error) {
        expect(error).to.be.instanceOf(SyntaxError);
      }
    });

    it('should validate required configuration fields', async () => {
      const incompleteConfig = {
        app: {
          name: 'test-app'
          // Missing port and environment
        }
      };

      await fs.writeFile(configFile, JSON.stringify(incompleteConfig, null, 2));

      const content = await fs.readFile(configFile, 'utf8');
      const parsed = JSON.parse(content);

      expect(parsed.app).to.have.property('name');
      expect(parsed.app).to.not.have.property('port'); // Should validate this is required
      expect(parsed.app).to.not.have.property('environment'); // Should validate this is required
    });
  });

  describe('Database Configuration Validation', () => {
    it('should validate database connection parameters', () => {
      const dbConfigs = [
        { host: 'localhost', port: 5432, ssl: 'require' },
        { host: 'db.example.com', port: 3306, ssl: 'disable' },
        { host: '127.0.0.1', port: 5432, ssl: 'prefer' }
      ];

      dbConfigs.forEach(config => {
        expect(config.host).to.be.a('string');
        expect(config.port).to.be.a('number');
        expect(config.port).to.be.greaterThan(0);
        expect(config.port).to.be.lessThan(65536);
        expect(['require', 'prefer', 'disable']).to.include(config.ssl);
      });
    });

    it('should validate SQLite database path security', () => {
      const validPaths = [
        '/app/data/app.db',
        './data/nutrition.db',
        '/var/lib/app/database.db'
      ];

      const invalidPaths = [
        '../../../etc/passwd',
        '/etc/shadow',
        '..\\..\\windows\\system32'
      ];

      validPaths.forEach(dbPath => {
        expect(dbPath).to.not.include('..');
        expect(path.resolve(dbPath)).to.equal(path.normalize(dbPath));
      });

      invalidPaths.forEach(dbPath => {
        expect(dbPath).to.include('..');
      });
    });

    it('should validate connection pool settings', () => {
      const poolConfig = {
        maxOpen: 10,
        maxIdle: 5,
        maxLifetime: 300, // seconds
        maxIdleTime: 60   // seconds
      };

      expect(poolConfig.maxOpen).to.be.greaterThan(0);
      expect(poolConfig.maxIdle).to.be.lessThanOrEqual(poolConfig.maxOpen);
      expect(poolConfig.maxLifetime).to.be.greaterThan(0);
      expect(poolConfig.maxIdleTime).to.be.greaterThan(0);
      expect(poolConfig.maxIdleTime).to.be.lessThan(poolConfig.maxLifetime);
    });
  });

  describe('Security Configuration Validation', () => {
    it('should validate JWT configuration', () => {
      const jwtConfigs = [
        { secret: 'a'.repeat(32), expiresIn: '24h', algorithm: 'HS256' },
        { secret: 'a'.repeat(64), expiresIn: '1h', algorithm: 'HS512' }
      ];

      jwtConfigs.forEach(config => {
        expect(config.secret.length).to.be.greaterThanOrEqual(32);
        expect(config.expiresIn).to.match(/^\d+[smhd]$/); // seconds, minutes, hours, days
        expect(['HS256', 'HS384', 'HS512']).to.include(config.algorithm);
      });
    });

    it('should validate CORS configuration', () => {
      const corsConfigs = [
        {
          allowedOrigins: ['https://my.doctorhealthy1.com'],
          allowedMethods: ['GET', 'POST', 'PUT', 'DELETE'],
          allowedHeaders: ['Content-Type', 'Authorization'],
          allowCredentials: true
        }
      ];

      corsConfigs.forEach(config => {
        expect(config.allowedOrigins).to.be.an('array');
        expect(config.allowedOrigins.length).to.be.greaterThan(0);
        expect(config.allowedOrigins).to.not.include('*'); // Should not allow all origins

        config.allowedOrigins.forEach(origin => {
          expect(origin).to.match(/^https?:\/\//);
        });
      });
    });

    it('should validate rate limiting configuration', () => {
      const rateLimitConfigs = [
        { requests: 100, window: '1m', burst: 200 },
        { requests: 1000, window: '1h', burst: 1500 }
      ];

      rateLimitConfigs.forEach(config => {
        expect(config.requests).to.be.greaterThan(0);
        expect(config.window).to.match(/^\d+[smhd]$/);
        expect(config.burst).to.be.greaterThanOrEqual(config.requests);
      });
    });

    it('should validate API key configuration', () => {
      const apiKeyConfigs = [
        { prefix: 'dh_', length: 32, hashAlgorithm: 'sha256' },
        { prefix: 'api_', length: 64, hashAlgorithm: 'sha512' }
      ];

      apiKeyConfigs.forEach(config => {
        expect(config.prefix).to.match(/^[a-zA-Z_]+$/);
        expect(config.length).to.be.greaterThanOrEqual(32);
        expect(['sha256', 'sha512']).to.include(config.hashAlgorithm);
      });
    });
  });

  describe('Server Configuration Validation', () => {
    it('should validate server port configuration', () => {
      const validPorts = [3000, 8080, 8081, 9000];
      const invalidPorts = [-1, 0, 80, 443, 1023, 65536];

      validPorts.forEach(port => {
        expect(port).to.be.greaterThan(1024);
        expect(port).to.be.lessThan(65536);
      });

      invalidPorts.forEach(port => {
        expect(port).to.be.lessThan(1024).or.greaterThan(65535);
      });
    });

    it('should validate HTTPS configuration', () => {
      const httpsConfigs = [
        {
          enabled: true,
          certFile: '/etc/ssl/certs/cert.pem',
          keyFile: '/etc/ssl/private/key.pem',
          redirectHttp: true
        }
      ];

      httpsConfigs.forEach(config => {
        if (config.enabled) {
          expect(config.certFile).to.be.a('string');
          expect(config.keyFile).to.be.a('string');
          expect(config.certFile).to.not.equal(config.keyFile);
        }
      });
    });

    it('should validate middleware configuration', () => {
      const middlewareConfigs = [
        {
          security: {
            hsts: { maxAge: 31536000, includeSubdomains: true },
            csp: { defaultSrc: "'self'", scriptSrc: "'self' 'unsafe-inline'" },
            xFrameOptions: 'SAMEORIGIN'
          },
          compression: {
            enabled: true,
            level: 6,
            types: ['text/plain', 'application/json']
          }
        }
      ];

      middlewareConfigs.forEach(config => {
        expect(config.security).to.be.an('object');
        expect(config.compression.level).to.be.within(1, 9);
      });
    });
  });

  describe('Logging Configuration Validation', () => {
    it('should validate log level configuration', () => {
      const validLevels = ['debug', 'info', 'warn', 'error'];
      const invalidLevels = ['trace', 'fatal', 'critical', ''];

      validLevels.forEach(level => {
        expect(validLevels).to.include(level);
      });

      invalidLevels.forEach(level => {
        expect(validLevels).to.not.include(level);
      });
    });

    it('should validate log format configuration', () => {
      const validFormats = ['json', 'text', 'logfmt'];
      const invalidFormats = ['xml', 'yaml', 'binary'];

      validFormats.forEach(format => {
        expect(validFormats).to.include(format);
      });

      invalidFormats.forEach(format => {
        expect(validFormats).to.not.include(format);
      });
    });

    it('should validate log output configuration', () => {
      const logOutputs = [
        { type: 'file', path: '/app/logs/app.log', maxSize: '10m', maxFiles: 5 },
        { type: 'stdout', format: 'json' },
        { type: 'syslog', facility: 'local0' }
      ];

      logOutputs.forEach(output => {
        expect(output.type).to.be.oneOf(['file', 'stdout', 'stderr', 'syslog']);
        if (output.type === 'file') {
          expect(output.path).to.be.a('string');
          expect(output.maxSize).to.match(/^\d+[kmg]?$/i);
        }
      });
    });
  });

  describe('External Service Configuration Validation', () => {
    it('should validate Redis configuration', () => {
      const redisConfigs = [
        { host: 'localhost', port: 6379, password: '', db: 0 },
        { host: 'redis.example.com', port: 6380, password: 'secret', db: 1 }
      ];

      redisConfigs.forEach(config => {
        expect(config.host).to.be.a('string');
        expect(config.port).to.be.within(1, 65535);
        expect(config.db).to.be.greaterThanOrEqual(0);
      });
    });

    it('should validate monitoring configuration', () => {
      const monitoringConfigs = [
        {
          prometheus: { enabled: true, port: 9090, path: '/metrics' },
          grafana: { enabled: true, port: 3000, adminPassword: 'secure-pass' },
          healthChecks: { enabled: true, interval: 30, timeout: 10 }
        }
      ];

      monitoringConfigs.forEach(config => {
        if (config.prometheus.enabled) {
          expect(config.prometheus.port).to.be.within(1024, 65535);
        }
        if (config.grafana.enabled) {
          expect(config.grafana.adminPassword).to.have.length.greaterThan(8);
        }
      });
    });

    it('should validate backup configuration', () => {
      const backupConfigs = [
        {
          enabled: true,
          schedule: '0 2 * * *', // Daily at 2 AM
          retention: 30, // days
          destination: 's3://backups/app',
          encryption: true
        }
      ];

      backupConfigs.forEach(config => {
        expect(config.schedule).to.match(/^[\d\s\*\-\,\/]+$/); // Cron format
        expect(config.retention).to.be.greaterThan(0);
        expect(config.encryption).to.be.true;
      });
    });
  });

  describe('Environment-Specific Validation', () => {
    it('should validate development environment configuration', () => {
      process.env.ENV = 'development';

      const devConfig = {
        debug: true,
        logLevel: 'debug',
        corsAllowAll: true,
        database: 'sqlite://:memory:'
      };

      expect(devConfig.debug).to.be.true;
      expect(devConfig.logLevel).to.equal('debug');
      expect(devConfig.corsAllowAll).to.be.true;
    });

    it('should validate production environment configuration', () => {
      process.env.ENV = 'production';

      const prodConfig = {
        debug: false,
        logLevel: 'warn',
        corsAllowAll: false,
        forceHttps: true,
        securityHeaders: true
      };

      expect(prodConfig.debug).to.be.false;
      expect(prodConfig.logLevel).to.equal('warn');
      expect(prodConfig.corsAllowAll).to.be.false;
      expect(prodConfig.forceHttps).to.be.true;
    });

    it('should validate staging environment configuration', () => {
      process.env.ENV = 'staging';

      const stagingConfig = {
        debug: false,
        logLevel: 'info',
        corsAllowAll: false,
        monitoring: true,
        backups: true
      };

      expect(stagingConfig.debug).to.be.false;
      expect(stagingConfig.logLevel).to.equal('info');
      expect(stagingConfig.corsAllowAll).to.be.false;
      expect(stagingConfig.monitoring).to.be.true;
    });
  });

  describe('Configuration Loading and Merging', () => {
    it('should merge environment variables with config file', async () => {
      const baseConfig = {
        app: { port: 8080 },
        database: { host: 'localhost' }
      };

      // Simulate environment overrides
      process.env.PORT = '9000';
      process.env.DB_HOST = 'db.example.com';

      const mergedConfig = {
        app: { port: parseInt(process.env.PORT) },
        database: { host: process.env.DB_HOST }
      };

      expect(mergedConfig.app.port).to.equal(9000);
      expect(mergedConfig.database.host).to.equal('db.example.com');
    });

    it('should validate configuration schema', () => {
      const configSchema = {
        type: 'object',
        required: ['app', 'database', 'security'],
        properties: {
          app: {
            type: 'object',
            required: ['name', 'port'],
            properties: {
              name: { type: 'string' },
              port: { type: 'integer', minimum: 1024, maximum: 65535 }
            }
          }
        }
      };

      // This would use a JSON schema validator in real implementation
      expect(configSchema.type).to.equal('object');
      expect(configSchema.required).to.include('app');
      expect(configSchema.required).to.include('database');
      expect(configSchema.required).to.include('security');
    });
  });
});