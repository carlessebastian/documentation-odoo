# /projects/{projectId}

Get a specific payment.

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
      "get": {
        "operationId": "Get Project",
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
                    "category": {
                      "type": "integer"
                    },
                    "contactId": {
                      "type": "string"
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
                    "expenses": {
                      "type": "object",
                      "properties": {
                        "docId": {
                          "type": "string"
                        },
                        "type": {
                          "type": "string"
                        },
                        "subtotal": {
                          "type": "integer"
                        },
                        "desc": {
                          "type": "string"
                        },
                        "invoiceNum": {
                          "type": "string"
                        },
                        "total": {
                          "type": "integer"
                        },
                        "contactId": {
                          "type": "string"
                        },
                        "contactName": {
                          "type": "string"
                        },
                        "date": {
                          "type": "integer"
                        },
                        "dueDate": {
                          "type": "integer"
                        }
                      }
                    },
                    "estimates": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "docId": {
                            "type": "string"
                          },
                          "type": {
                            "type": "string"
                          },
                          "subtotal": {
                            "type": "integer"
                          },
                          "desc": {
                            "type": "string"
                          },
                          "invoiceNum": {
                            "type": "string"
                          },
                          "total": {
                            "type": "number"
                          },
                          "contactId": {
                            "type": "string"
                          },
                          "contactName": {
                            "type": "string"
                          },
                          "date": {
                            "type": "integer"
                          },
                          "dueDate": {
                            "type": "integer"
                          }
                        }
                      }
                    },
                    "sales": {
                      "type": "array",
                      "items": {
                        "type": "object",
                        "properties": {
                          "docId": {
                            "type": "string"
                          },
                          "type": {
                            "type": "string"
                          },
                          "subtotal": {
                            "type": "number"
                          },
                          "desc": {
                            "type": "string"
                          },
                          "invoiceNum": {
                            "type": "string"
                          },
                          "total": {
                            "type": "integer"
                          },
                          "contactId": {
                            "type": "string"
                          },
                          "contactName": {
                            "type": "string"
                          },
                          "date": {
                            "type": "integer"
                          },
                          "dueDate": {
                            "type": "integer"
                          }
                        }
                      }
                    },
                    "timeTracking": {
                      "type": "object",
                      "properties": {
                        "timeId": {
                          "type": "string"
                        },
                        "time": {
                          "type": "integer"
                        },
                        "desc": {
                          "type": "string"
                        },
                        "costHour": {
                          "type": "integer"
                        },
                        "userId": {
                          "type": "string"
                        },
                        "taskId": {
                          "type": "string"
                        },
                        "total": {
                          "type": "number"
                        }
                      }
                    },
                    "price": {
                      "type": "integer"
                    },
                    "numberOfTasks": {
                      "type": "integer"
                    },
                    "completedTasks": {
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
                },
                "examples": {
                  "response": {
                    "value": {
                      "id": "5ab390311d6d82002432ec5a",
                      "name": "Building 301",
                      "desc": "Bulding 301 in Barcelona",
                      "tags": [
                        "tag",
                        "tog",
                        "tug"
                      ],
                      "category": 0,
                      "contactId": "5aaa51ab5b70640028340186",
                      "contactName": "DIvero",
                      "date": 0,
                      "dueDate": 0,
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
                      "expenses": {
                        "docId": "5ab3d4121d6d820062013ed3",
                        "type": "purchase",
                        "subtotal": 200,
                        "desc": "noooooo",
                        "invoiceNum": "123",
                        "total": 242,
                        "contactId": "5aaa51ab5b70640028340186",
                        "contactName": "DIvero (Divero)",
                        "date": 1521673200,
                        "dueDate": 1521759600
                      },
                      "estimates": [
                        {
                          "docId": "5ab3d4cc1d6d82007711bba3",
                          "type": "estimate",
                          "subtotal": 34433,
                          "desc": "no desc",
                          "invoiceNum": "E170001",
                          "total": 41663.93,
                          "contactId": "5aaa51ab5b70640028340186",
                          "contactName": "DIvero (Divero)",
                          "date": 1517871600,
                          "dueDate": 1520118000
                        }
                      ],
                      "sales": [
                        {
                          "docId": "5ab391071d6d820034294783",
                          "type": "invoice",
                          "subtotal": 818.18,
                          "desc": "",
                          "invoiceNum": "F170001",
                          "total": 990,
                          "contactId": "5aa939a95b70640009653d72",
                          "contactName": "Bose QC",
                          "date": 1521673200,
                          "dueDate": 0
                        }
                      ],
                      "timeTracking": {
                        "timeId": "5ac4f2cec839ea004e18a463",
                        "time": 45300,
                        "desc": "POOOOOSTuuuuuuu eeeee timetracking after refactor",
                        "costHour": 234,
                        "userId": "5a05cc5a60cea100094baf22",
                        "taskId": "5ab3cb7d1d6d8200440d4683",
                        "total": 2944.5
                      },
                      "price": 2345,
                      "numberOfTasks": 6,
                      "completedTasks": 3,
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
                }
              }
            }
          }
        },
        "tags": [
          "PROJECTS"
        ],
        "description": "Get a specific payment."
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