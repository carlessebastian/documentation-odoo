# Update an employee

Update an employee.

# OpenAPI definition

```json
{
  "openapi": "3.0.0",
  "info": {
    "description": "The Holded's Team API is organized around REST, using HTTP responses code to keep you informed about what's going on. Our endpoints will returns you metada in JSON format directly from Holded.",
    "version": "1.0.1",
    "title": "Team API",
    "contact": {
      "email": "developers@holded.com"
    }
  },
  "x-samples-languages": [
    "curl",
    "node",
    "ruby",
    "python"
  ],
  "security": [
    {
      "Auth": []
    }
  ],
  "tags": [
    {
      "name": "Employees",
      "description": "CRUD Employees"
    }
  ],
  "paths": {
    "/employees/{employeeId}": {
      "parameters": [
        {
          "name": "employeeId",
          "in": "path",
          "required": true,
          "schema": {
            "type": "string"
          }
        }
      ],
      "put": {
        "tags": [
          "Employees"
        ],
        "summary": "Update an employee",
        "operationId": "Update Employee",
        "description": "Update an employee.",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "name": {
                    "type": "string"
                  },
                  "lastName": {
                    "type": "string"
                  },
                  "mainEmail": {
                    "type": "string"
                  },
                  "email": {
                    "type": "string"
                  },
                  "nationality": {
                    "type": "string"
                  },
                  "phone": {
                    "type": "string"
                  },
                  "mobile": {
                    "type": "string"
                  },
                  "dateOfBirth": {
                    "type": "string",
                    "description": "dd/mm/yyyy"
                  },
                  "gender": {
                    "type": "string",
                    "description": "male or female"
                  },
                  "mainLanguage": {
                    "type": "string",
                    "description": "options = English, English(UK), English(US), English(Canada), Spanish, Spanish(Spain), Spanish(Mexico), Spanish(Argentina), Spanish(Colombia), Portuguese, Portuguese(Portugal), Portuguese(Brazil), Catalan, Galician, Euskera, French, German(Deutsch), Italian, Greek, Swedish, Dutch, Finnish, Irish, Norwegian, Danish, Czech, Croatian, Russian, Polish"
                  },
                  "iban": {
                    "type": "string"
                  },
                  "timeOffPolicyId": {
                    "type": "string"
                  },
                  "timeOffSupervisors": {
                    "type": "array",
                    "items": {
                      "type": "string"
                    },
                    "description": "containing employeesId"
                  },
                  "reportingTo": {
                    "type": "string",
                    "description": "should be an employeeId"
                  },
                  "code": {
                    "type": "string",
                    "description": "nif"
                  },
                  "socialSecurityNum": {
                    "type": "string"
                  },
                  "address": {
                    "type": "object",
                    "properties": {
                      "address": {
                        "type": "string"
                      },
                      "city": {
                        "type": "string"
                      },
                      "postalCode": {
                        "type": "string"
                      },
                      "province": {
                        "type": "string"
                      },
                      "country": {
                        "type": "string"
                      }
                    }
                  },
                  "fiscalResidence": {
                    "type": "boolean"
                  },
                  "fiscalAddress": {
                    "type": "object",
                    "description": "You need to set fiscalResidence to false in order to be able to send a fiscalAdress",
                    "properties": {
                      "idNum": {
                        "type": "string"
                      },
                      "address": {
                        "type": "string"
                      },
                      "city": {
                        "type": "string"
                      },
                      "cityOfBirth": {
                        "type": "string"
                      },
                      "postalCode": {
                        "type": "string"
                      },
                      "province": {
                        "type": "string"
                      },
                      "country": {
                        "type": "string"
                      },
                      "countryOfBirth": {
                        "type": "string"
                      },
                      "endSituationDate": {
                        "type": "string"
                      }
                    }
                  },
                  "workplace": {
                    "type": "string",
                    "description": "workplace ID"
                  },
                  "teams": {
                    "type": "array",
                    "description": "array of strings containing team ID's",
                    "items": {
                      "type": "string"
                    }
                  },
                  "holdedUserId": {
                    "type": "string"
                  }
                }
              }
            }
          },
          "description": "Employee to update"
        },
        "responses": {
          "200": {
            "description": "employee updated",
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
                }
              }
            }
          }
        }
      }
    }
  },
  "servers": [
    {
      "url": "https://api.holded.com/api/team/v1"
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
  }
}
```