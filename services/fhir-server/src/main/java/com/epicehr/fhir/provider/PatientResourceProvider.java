package com.epicehr.fhir.provider;

import ca.uhn.fhir.rest.annotation.IdParam;
import ca.uhn.fhir.rest.annotation.Read;
import ca.uhn.fhir.rest.annotation.Search;
import ca.uhn.fhir.rest.server.IResourceProvider;
import ca.uhn.fhir.rest.server.exceptions.ResourceNotFoundException;
import org.hl7.fhir.r4.model.IdType;
import org.hl7.fhir.r4.model.Patient;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * FHIR Patient Resource Provider
 * Handles Patient resource operations for EPIC EHR integration
 */
@Component
public class PatientResourceProvider implements IResourceProvider {

    private Map<String, Patient> patients = new HashMap<>();

    public PatientResourceProvider() {
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

    @Override
    public Class<Patient> getResourceType() {
        return Patient.class;
    }

    /**
     * Read a single patient by ID
     */
    @Read
    public Patient read(@IdParam IdType theId) {
        Patient patient = patients.get(theId.getIdPart());
        if (patient == null) {
            throw new ResourceNotFoundException("Patient not found: " + theId.getIdPart());
        }
        return patient;
    }

    /**
     * Search for patients
     */
    @Search
    public List<Patient> search() {
        return new ArrayList<>(patients.values());
    }
}
