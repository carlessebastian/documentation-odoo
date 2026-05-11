# /tasks/{taskId}

Get a specific task.

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
    "/tasks/{taskId}": {
      "parameters": [
        {
          "name": "taskId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "get": {
        "operationId": "Get Task",
        "responses": {
          "200": {
            "description": "",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "id": {
                      "type": "string"
                    },
                    "projectId": {
                      "type": "string"
                    },
                    "listId": {
                      "type": "string"
                    },
                    "name": {
                      "type": "string"
                    },
                    "desc": {
                      "type": "string"
                    },
                    "labels": {
                      "type": "array",
                      "items": {
                        "type": "string"
                      }
                    },
                    "comments": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "commentId": {
                            "type": "string"
                          },
                          "createdAt": {
                            "type": "integer"
                          },
                          "userId": {
                            "type": "string"
                          },
                          "message": {
                            "type": "string"
                          }
                        }
                      }
                    },
                    "date": {
                      "type": "integer"
                    },
                    "dueDate": {
                      "type": "integer"
                    },
                    "userId": {
                      "type": "string"
                    },
                    "createdAt": {
                      "type": "integer"
                    },
                    "updatedAt": {
                      "type": "integer"
                    },
                    "status": {
                      "type": "integer"
                    },
                    "billable": {
                      "type": "integer"
                    },
                    "featured": {
                      "type": "integer"
                    }
                  }
                },
                "examples": {
                  "response": {
                    "value": {
                      "id": "5ab3df6e1d6d82008c5777a4",
                      "projectId": "5ab390311d6d82002432ec5a",
                      "listId": "5ab390311d6d82002432ec53",
                      "name": "Business plan",
                      "desc": "business plan for the new project",
                      "labels": [
                        "5ab390311d6d82002432ec58",
                        "5ab390311d6d82002432ec59"
                      ],
                      "comments": [
                        {
                          "commentId": "5ab3df8c1d6d820088525aa3",
                          "createdAt": 1521737612,
                          "userId": "5a05cc5a60cea100094baf22",
                          "message": "no comments"
                        },
                        {
                          "commentId": "5ab3df971d6d82008c5777a5",
                          "createdAt": 1521737623,
                          "userId": "5a05cc5a60cea100094baf22",
                          "message": "a piece of comment\n"
                        }
                      ],
                      "date": 1521737582,
                      "dueDate": 1521673200,
                      "userId": "5a05cc5a60cea100094baf22",
                      "createdAt": 1521737582,
                      "updatedAt": 1521737582,
                      "status": 0,
                      "billable": 0,
                      "featured": 1
                    }
                  }
                }
              }
            }
          }
        },
        "tags": [
          "TASKS"
        ],
        "description": "Get a specific task."
      }
    }
  },
  "x-samples-enabled": true,
  "tags": [
    {
      "name": "TASKS"
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