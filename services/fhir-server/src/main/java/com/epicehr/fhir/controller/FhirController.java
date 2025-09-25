package com.epicehr.fhir.controller;

import ca.uhn.fhir.context.FhirContext;
import ca.uhn.fhir.parser.IParser;
import org.hl7.fhir.r4.model.Patient;
import org.hl7.fhir.r4.model.IdType;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * FHIR REST Controller
 * Provides FHIR endpoints for EPIC EHR integration
 */
@RestController
@RequestMapping("/fhir")
@CrossOrigin(origins = "*")
public class FhirController {

    @Autowired
    private FhirContext fhirContext;
    
    private final Map<String, Patient> patients = new HashMap<>();

    public FhirController() {
        // Initialize with sample patient data
        Patient patient1 = new Patient();
        patient1.setId("1");
        patient1.addName().setFamily("Doe").addGiven("John");
        patient1.addIdentifier().setSystem("http://epic.com/patient-id").setValue("EPIC123");
        patients.put("1", patient1);

        Patient patient2 = new Patient();
        patient2.setId("2");
        patient2.addName().setFamily("Smith").addGiven("Jane");
        patient2.addIdentifier().setSystem("http://epic.com/patient-id").setValue("EPIC456");
        patients.put("2", patient2);
    }

    /**
     * Get server metadata/capability statement
     */
    @GetMapping(value = "/metadata", produces = MediaType.APPLICATION_JSON_VALUE)
    public String getMetadata() {
        return "{\n" +
                "  \"resourceType\": \"CapabilityStatement\",\n" +
                "  \"id\": \"epic-fhir-server\",\n" +
                "  \"name\": \"EPIC EHR FHIR Server\",\n" +
                "  \"version\": \"1.0.0\",\n" +
                "  \"status\": \"active\",\n" +
                "  \"date\": \"2025-01-01\",\n" +
                "  \"publisher\": \"EPIC EHR Integration\",\n" +
                "  \"kind\": \"instance\",\n" +
                "  \"software\": {\n" +
                "    \"name\": \"EPIC FHIR Server\",\n" +
                "    \"version\": \"1.0.0\"\n" +
                "  },\n" +
                "  \"fhirVersion\": \"4.0.1\",\n" +
                "  \"format\": [\"json\", \"xml\"],\n" +
                "  \"rest\": [{\n" +
                "    \"mode\": \"server\",\n" +
                "    \"resource\": [{\n" +
                "      \"type\": \"Patient\",\n" +
                "      \"interaction\": [\n" +
                "        {\"code\": \"read\"},\n" +
                "        {\"code\": \"search-type\"}\n" +
                "      ]\n" +
                "    }]\n" +
                "  }]\n" +
                "}";
    }

    /**
     * Get all patients
     */
    @GetMapping(value = "/Patient", produces = MediaType.APPLICATION_JSON_VALUE)
    public String searchPatients() {
        List<Patient> patientList = new ArrayList<>(patients.values());
        IParser parser = fhirContext.newJsonParser().setPrettyPrint(true);
        
        StringBuilder bundle = new StringBuilder();
        bundle.append("{\n");
        bundle.append("  \"resourceType\": \"Bundle\",\n");
        bundle.append("  \"type\": \"searchset\",\n");
        bundle.append("  \"total\": ").append(patientList.size()).append(",\n");
        bundle.append("  \"entry\": [\n");
        
        for (int i = 0; i < patientList.size(); i++) {
            if (i > 0) bundle.append(",\n");
            bundle.append("    {\n");
            bundle.append("      \"resource\": ");
            bundle.append(parser.encodeResourceToString(patientList.get(i)));
            bundle.append("\n    }");
        }
        
        bundle.append("\n  ]\n");
        bundle.append("}");
        
        return bundle.toString();
    }

    /**
     * Get patient by ID
     */
    @GetMapping(value = "/Patient/{id}", produces = MediaType.APPLICATION_JSON_VALUE)
    public String getPatient(@PathVariable String id) {
        try {
            Patient patient = patients.get(id);
            if (patient == null) {
                return "{\"resourceType\": \"OperationOutcome\", \"issue\": [{\"severity\": \"error\", \"code\": \"not-found\", \"diagnostics\": \"Patient not found: " + id + "\"}]}";
            }
            IParser parser = fhirContext.newJsonParser().setPrettyPrint(true);
            return parser.encodeResourceToString(patient);
        } catch (Exception e) {
            return "{\"resourceType\": \"OperationOutcome\", \"issue\": [{\"severity\": \"error\", \"code\": \"exception\", \"diagnostics\": \"" + e.getMessage() + "\"}]}";
        }
    }

    /**
     * Health check endpoint
     */
    @GetMapping(value = "/health", produces = MediaType.APPLICATION_JSON_VALUE)
    public String health() {
        return "{\"status\": \"UP\", \"server\": \"EPIC EHR FHIR Server\", \"version\": \"1.0.0\"}";
    }
}
