# /projects/{projectId}

Delete a specific project.

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
    "/projects/{projectId}": {
      "parameters": [
        {
          "name": "projectId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "delete": {
        "operationId": "Delete Project",
        "responses": {
          "200": {
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
                      "info": "Successfully deleted",
                      "id": "5aba68b1c5d438006425ad45"
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
        "description": "Delete a specific project."
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