package com.epicehr.fhir.config;

import ca.uhn.fhir.context.FhirContext;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * FHIR Server Configuration for EPIC EHR Integration
 * Simplified configuration for stable operation
 */
@Configuration
public class FhirConfig {

    /**
     * FHIR Context for R4
     */
    @Bean
    public FhirContext fhirContext() {
        return FhirContext.forR4();
    }
}
