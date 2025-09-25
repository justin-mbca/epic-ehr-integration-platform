package com.epicehr.fhir.controller;

import ca.uhn.fhir.context.FhirContext;
import ca.uhn.fhir.parser.IParser;
import com.epicehr.fhir.provider.PatientResourceProvider;
import org.hl7.fhir.r4.model.Patient;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * FHIR REST Controller
 * Provides FHIR endpoints for EPIC EHR integration
 */
@RestController
@RequestMapping("/fhir")
public class FhirController {

    @Autowired
    private FhirContext fhirContext;
    
    private final PatientResourceProvider patientProvider = new PatientResourceProvider();

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
        List<Patient> patients = patientProvider.search();
        IParser parser = fhirContext.newJsonParser().setPrettyPrint(true);
        
        StringBuilder bundle = new StringBuilder();
        bundle.append("{\n");
        bundle.append("  \"resourceType\": \"Bundle\",\n");
        bundle.append("  \"type\": \"searchset\",\n");
        bundle.append("  \"total\": ").append(patients.size()).append(",\n");
        bundle.append("  \"entry\": [\n");
        
        for (int i = 0; i < patients.size(); i++) {
            if (i > 0) bundle.append(",\n");
            bundle.append("    {\n");
            bundle.append("      \"resource\": ");
            bundle.append(parser.encodeResourceToString(patients.get(i)));
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
            Patient patient = patientProvider.read(new org.hl7.fhir.r4.model.IdType(id));
            IParser parser = fhirContext.newJsonParser().setPrettyPrint(true);
            return parser.encodeResourceToString(patient);
        } catch (Exception e) {
            return "{\"resourceType\": \"OperationOutcome\", \"issue\": [{\"severity\": \"error\", \"code\": \"not-found\", \"diagnostics\": \"Patient not found: " + id + "\"}]}";
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
