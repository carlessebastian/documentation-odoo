# /projects/{projectId}

Update a specific project.

Only the params included in the operation will update the project.

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
      "put": {
        "operationId": "Update Project",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {
                    "type": "string"
                  },
                  "desc": {
                    "type": "string"
                  },
                  "tags": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    }
                  },
                  "contactName": {
                    "type": "string"
                  },
                  "date": {
                    "type": "integer"
                  },
                  "dueDate": {
                    "type": "integer"
                  },
                  "status": {
                    "type": "integer"
                  },
                  "lists": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "id": {
                          "type": "string"
                        },
                        "key": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "desc": {
                          "type": "string"
                        }
                      }
                    }
                  },
                  "billable": {
                    "type": "integer"
                  },
                  "price": {
                    "type": "integer"
                  },
                  "labels": {
                    "type": "array",
                    "items": {
                      "type": "object",
                      "properties": {
                        "id": {
                          "type": "string"
                        },
                        "name": {
                          "type": "string"
                        },
                        "color": {
                          "type": "string"
                        }
                      }
                    }
                  }
                }
              }
            }
          },
          "x-examples": {
            "application/json": {
              "name": "Building 301",
              "desc": "Bulding 301 in Barcelona",
              "tags": [
                "tag",
                "tog",
                "tug"
              ],
              "contactName": "DIvero",
              "date": 1521673200,
              "dueDate": 1521759600,
              "status": 2,
              "lists": [
                {
                  "id": "5ab390311d6d82002432ec52",
                  "key": "pending",
                  "name": "Pending",
                  "desc": "nan"
                },
                {
                  "id": "5ab390311d6d82002432ec53",
                  "key": "review",
                  "name": "Review",
                  "desc": "nan"
                },
                {
                  "id": "5ab390311d6d82002432ec54",
                  "key": "done",
                  "name": "Done",
                  "desc": "nan"
                }
              ],
              "billable": 1,
              "price": 2345,
              "labels": [
                {
                  "id": "5ab390311d6d82002432ec55",
                  "name": "New",
                  "color": "#10cf91"
                },
                {
                  "id": "5ab390311d6d82002432ec56",
                  "name": "Confirmed",
                  "color": "#10cf91"
                },
                {
                  "id": "5ab390311d6d82002432ec57",
                  "name": "Pending",
                  "color": "#f8d053"
                },
                {
                  "id": "5ab390311d6d82002432ec58",
                  "name": "Fixed",
                  "color": "#4181f2"
                },
                {
                  "id": "5ab390311d6d82002432ec59",
                  "name": "Urgent",
                  "color": "#ee585d"
                }
              ]
            }
          }
        },
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
                      "info": "Updated",
                      "id": "5ab390311d6d82002432ec5a"
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
        "description": "Update a specific project.\n\nOnly the params included in the operation will update the project."
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