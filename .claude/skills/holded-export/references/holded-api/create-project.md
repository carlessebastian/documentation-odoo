# /projects

Create a new project.

# OpenAPI definition

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Projects API",
    "version": "1.2",
    "description": "The Holded’s Projects API is organized around REST, using HTTP responses code to keep you informed about what’s going on. Our endpoints will returns you metada in JSON format directly from Holded."
  },
  "x-samples-languages": [
    "curl",
    "node",
    "ruby",
    "python"
  ],
  "paths": {
    "/projects": {
      "post": {
        "operationId": "Create Project",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {
                    "type": "string"
                  }
                },
                "required": [
                  "name"
                ]
              }
            }
          },
          "x-examples": {
            "application/json": {
              "name": "Project of the month"
            }
          }
        },
        "responses": {
          "201": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "status": {
                      "type": "integer"
                    },
                    "info": {
                      "type": "string"
                    },
                    "id": {
                      "type": "string"
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "status": 1,
                      "info": "Created",
                      "id": "5ac4f2cec839ea004e18a463"
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "PROJECTS"
        ],
        "description": "Create a new project."
      }
    }
  },
  "x-samples-enabled": true,
  "tags": [
    {
      "name": "PROJECTS"
    }
  ],
  "security": [
    {
      "Auth": []
    }
  ],
  "servers": [
    {
      "url": "https://api.holded.com/api/projects/v1"
    }
  ],
  "components": {
    "securitySchemes": {
      "Auth": {
        "type": "apiKey",
        "name": "key",
        "in": "header"
      }
    }
  },
  "x-readme": {
    "explorer-enabled": true,
    "proxy-enabled": true
  }
}
```