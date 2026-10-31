import { describe, expect, it } from 'vitest';
import { isFilled, isValidCuit, validateCpe } from './cpeFields';
import type { CpeData } from './cpeFields';

describe('Carta de Porte field validation', () => {
  it('validates CUIT check digits while retaining text identifiers', () => {
    expect(isValidCuit('30709590894')).toBe(true);
    expect(isValidCuit('30709590895')).toBe(false);
    expect(isValidCuit('3070959089')).toBe(false);
    expect(isFilled('000123')).toBe(true);
    expect(isFilled('0')).toBe(true);
  });

  it('requires explicit false values and calculates only non-negative weights', () => {
    const data: CpeData = {
      values: {
        requester_cuit: '20361814305',
        branch: '1',
        origin_mode: 'producer',
        origin_province: '4',
        origin_locality: '12',
        corresponds_producer_withdrawal: 'false',
        applicant_is_field: 'false',
        grain_code: '1',
        harvest: '2526',
        gross_weight: '0',
        tare_weight: '0',
        destination_cuit: '30709590894',
        destination_is_field: 'false',
        destination_province: '4',
        destination_locality: '12',
        recipient_cuit: '30700869918',
        carrier_cuit: '20361814305',
        domains: 'AJV636\nGRP753',
        departure: '2026-10-31T12:30',
        distance_km: '220',
        driver_cuit: '20361814305',
        freight_payer_cuit: '20361814305',
        fumigated: 'false'
      },
      status: {}
    };
    expect(validateCpe(data)).toEqual({});
    expect(isFilled(data.values.corresponds_producer_withdrawal)).toBe(true);
  });

  it('allows the same company in multiple commercial roles', () => {
    const data: CpeData = {
      values: {
        requester_cuit: '20361814305',
        branch: '1',
        origin_mode: 'producer',
        origin_province: '4',
        origin_locality: '12',
        corresponds_producer_withdrawal: 'false',
        applicant_is_field: 'false',
        grain_code: '1',
        harvest: '2526',
        gross_weight: '45000',
        tare_weight: '14500',
        destination_cuit: '30709590894',
        destination_is_field: 'false',
        destination_province: '4',
        destination_locality: '12',
        recipient_cuit: '30700869918',
        carrier_cuit: '20361814305',
        domains: 'AJV636',
        departure: '2026-10-31T12:30',
        distance_km: '220',
        driver_cuit: '20361814305',
        freight_payer_cuit: '20361814305',
        fumigated: 'false',
        role_primary_seller: '20361814305',
        role_secondary_seller: '20361814305'
      },
      status: {}
    };
    expect(validateCpe(data)).toEqual({});
  });
});
