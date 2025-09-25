const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const compression = require('compression');
const rateLimit = require('express-rate-limit');
const { body, validationResult } = require('express-validator');
const jwt = require('jsonwebtoken');
const winston = require('winston');
const { createProxyMiddleware } = require('http-proxy-middleware');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Logger configuration
const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: 'logs/error.log', level: 'error' }),
    new winston.transports.File({ filename: 'logs/combined.log' }),
    new winston.transports.Console({
      format: winston.format.simple()
    })
  ]
});

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      scriptSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
  hsts: {
    maxAge: 31536000,
    includeSubDomains: true,
    preload: true
  }
}));

// CORS configuration for healthcare environment
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

// Rate limiting for API protection
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false
});

app.use(limiter);
app.use(compression());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// JWT Authentication middleware
const authenticateToken = (req, res, next) => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    return res.status(401).json({ error: 'Access token required' });
  }

  jwt.verify(token, process.env.JWT_SECRET || 'fallback-secret', (err, user) => {
    if (err) {
      logger.error('JWT verification failed', { error: err.message });
      return res.status(403).json({ error: 'Invalid or expired token' });
    }
    req.user = user;
    next();
  });
};

// Audit logging middleware
const auditLogger = (req, res, next) => {
  const auditData = {
    timestamp: new Date().toISOString(),
    method: req.method,
    url: req.url,
    ip: req.ip,
    userAgent: req.get('User-Agent'),
    userId: req.user?.id || 'anonymous'
  };
  
  logger.info('API Access', auditData);
  next();
};

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'healthy', 
    timestamp: new Date().toISOString(),
    version: process.env.npm_package_version || '1.0.0'
  });
});

// FHIR endpoints proxy
const fhirServerUrl = process.env.FHIR_SERVER_URL || 'http://fhir-server:8084';

app.use('/fhir', authenticateToken, auditLogger, createProxyMiddleware({
  target: fhirServerUrl,
  changeOrigin: true,
  auth: 'admin:admin123', // Add basic auth for FHIR server
  onProxyReq: (proxyReq, req, res) => {
    // Log FHIR access
    logger.info('FHIR API Access', {
      endpoint: req.url,
      method: req.method,
      userId: req.user.id,
      targetUrl: `${fhirServerUrl}${req.url}`
    });
  },
  onError: (err, req, res) => {
    logger.error('FHIR Proxy Error', { error: err.message, url: req.url });
    res.status(502).json({ 
      error: 'FHIR service temporarily unavailable',
      message: err.message 
    });
  }
}));

// HL7 message endpoints
app.use('/hl7', authenticateToken, auditLogger, createProxyMiddleware({
  target: process.env.HL7_PROCESSOR_URL || 'http://hl7-processor:8001',
  changeOrigin: true,
  onProxyReq: (proxyReq, req, res) => {
    logger.info('HL7 Processor Access', {
      endpoint: req.url,
      method: req.method,
      userId: req.user.id
    });
  },
  onError: (err, req, res) => {
    logger.error('HL7 Proxy Error', { error: err.message, url: req.url });
    res.status(502).json({ 
      error: 'HL7 processor service temporarily unavailable',
      message: err.message 
    });
  }
}));

// Legacy HL7 message endpoint (for backwards compatibility)
app.post('/hl7/message', [
  authenticateToken,
  auditLogger,
  body('messageType').notEmpty().withMessage('Message type is required'),
  body('content').notEmpty().withMessage('HL7 content is required')
], (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }

  // Log HL7 message processing
  logger.info('HL7 Message Received', {
    messageType: req.body.messageType,
    userId: req.user.id,
    messageId: req.body.messageId
  });

  // Process HL7 message (implementation required)
  res.status(202).json({ 
    message: 'HL7 message queued for processing',
    messageId: req.body.messageId || Date.now().toString()
  });
});

// EPIC Connection Hub endpoints
app.use('/epic', authenticateToken, auditLogger, createProxyMiddleware({
  target: process.env.EPIC_CONNECTOR_URL || 'http://epic-connector:8002',
  changeOrigin: true,
  onProxyReq: (proxyReq, req, res) => {
    logger.info('EPIC Connection Hub Access', {
      endpoint: req.url,
      method: req.method,
      userId: req.user.id
    });
  },
  onError: (err, req, res) => {
    logger.error('EPIC Proxy Error', { error: err.message, url: req.url });
    res.status(502).json({ 
      error: 'EPIC connector service temporarily unavailable',
      message: err.message 
    });
  }
}));

// Audit Service endpoints
app.use('/audit', authenticateToken, auditLogger, createProxyMiddleware({
  target: process.env.AUDIT_SERVICE_URL || 'http://audit-service:8003',
  changeOrigin: true,
  onProxyReq: (proxyReq, req, res) => {
    logger.info('Audit Service Access', {
      endpoint: req.url,
      method: req.method,
      userId: req.user.id
    });
  },
  onError: (err, req, res) => {
    logger.error('Audit Proxy Error', { error: err.message, url: req.url });
    res.status(502).json({ 
      error: 'Audit service temporarily unavailable',
      message: err.message 
    });
  }
}));

// OAuth2 token endpoint
app.post('/oauth/token', [
  body('grant_type').equals('client_credentials'),
  body('client_id').notEmpty(),
  body('client_secret').notEmpty()
], (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }

  // Validate client credentials (implement proper validation)
  const { client_id, client_secret } = req.body;
  
  // Generate JWT token
  const token = jwt.sign(
    { 
      client_id,
      scope: 'fhir:read fhir:write hl7:process',
      iss: 'epic-ehr-gateway'
    },
    process.env.JWT_SECRET || 'fallback-secret',
    { expiresIn: '1h' }
  );

  logger.info('OAuth token issued', { client_id });

  res.json({
    access_token: token,
    token_type: 'Bearer',
    expires_in: 3600,
    scope: 'fhir:read fhir:write hl7:process'
  });
});

// Error handling middleware
app.use((err, req, res, next) => {
  logger.error('Unhandled error', { 
    error: err.message, 
    stack: err.stack,
    url: req.url,
    method: req.method
  });
  
  res.status(500).json({ 
    error: 'Internal server error',
    requestId: req.headers['x-request-id'] || Date.now().toString()
  });
});

// 404 handler
app.use('*', (req, res) => {
  res.status(404).json({ error: 'Endpoint not found' });
});

app.listen(PORT, () => {
  logger.info(`API Gateway running on port ${PORT}`);
});

module.exports = app;
