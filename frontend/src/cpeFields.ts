export type FieldStatus = 'ai' | 'edited' | 'confirmed';

export interface FieldDef {
  key: string;
  label: string;
}

export interface CpeData {
  values: Record<string, string>;
  status: Record<string, FieldStatus>;
}

export const ALL_FIELDS: FieldDef[] = [
  { key: 'requester_cuit', label: 'Solicitante/titular' },
  { key: 'branch', label: 'Sucursal' },
  { key: 'origin_mode', label: 'Modalidad de origen' },
  { key: 'origin_province', label: 'Provincia de origen' },
  { key: 'origin_locality', label: 'Localidad de origen' },
  { key: 'origin_plant', label: 'Planta de origen' },
  { key: 'origin_renspa', label: 'RENSPA' },
  { key: 'origin_latitude', label: 'Latitud' },
  { key: 'origin_longitude', label: 'Longitud' },
  { key: 'corresponds_producer_withdrawal', label: 'Retiro por el productor' },
  { key: 'applicant_is_field', label: 'Solicitante ubicado en campo' },
  { key: 'withdrawal_coe', label: 'Certificado COE' },
  { key: 'withdrawal_producer_cuit', label: 'Remitente comercial productor' },
  { key: 'role_primary_seller', label: 'Remitente comercial venta primaria' },
  { key: 'role_secondary_seller', label: 'Remitente comercial venta secundaria' },
  { key: 'role_secondary_seller_2', label: 'Remitente comercial venta secundaria 2' },
  { key: 'role_futures_market', label: 'Mercado a término' },
  { key: 'role_primary_broker', label: 'Corredor venta primaria' },
  { key: 'role_secondary_broker', label: 'Corredor venta secundaria' },
  { key: 'role_delivery_representative', label: 'Representante entregador' },
  { key: 'role_receiving_representative', label: 'Representante recibidor' },
  { key: 'grain_code', label: 'Grano/especie' },
  { key: 'harvest', label: 'Cosecha/campaña' },
  { key: 'gross_weight', label: 'Peso bruto' },
  { key: 'tare_weight', label: 'Peso tara' },
  { key: 'destination_cuit', label: 'Destino físico' },
  { key: 'destination_is_field', label: 'Destino es campo' },
  { key: 'destination_province', label: 'Provincia de destino' },
  { key: 'destination_locality', label: 'Localidad de destino' },
  { key: 'destination_plant', label: 'Planta de destino' },
  { key: 'recipient_cuit', label: 'Destinatario' },
  { key: 'carrier_cuit', label: 'Transportista' },
  { key: 'domains', label: 'Dominios' },
  { key: 'departure', label: 'Fecha y hora de partida' },
  { key: 'distance_km', label: 'Kilómetros a recorrer' },
  { key: 'turn_code', label: 'Código de turno' },
  { key: 'driver_cuit', label: 'Chofer' },
  { key: 'fare', label: 'Tarifa informada' },
  { key: 'freight_payer_cuit', label: 'Pagador del flete' },
  { key: 'freight_intermediary_cuit', label: 'Intermediario del flete' },
  { key: 'fumigated', label: 'Mercadería fumigada' },
  { key: 'observations', label: 'Observaciones' }
];

export function readCpeData(payload: Record<string, unknown>): CpeData {
  const rawValues = (payload.cpe ?? {}) as Record<string, unknown>;
  const rawStatus = (payload.field_status ?? {}) as Record<string, unknown>;
  const values: Record<string, string> = {};
  const status: Record<string, FieldStatus> = {};
  Object.entries(rawValues).forEach(([key, value]) => {
    if (typeof value === 'string' || typeof value === 'number') values[key] = String(value);
  });
  for (const f of ALL_FIELDS) {
    const v = rawValues[f.key];
    if (v !== undefined && v !== null) values[f.key] = String(v);
    const s = rawStatus[f.key];
    if (s === 'ai' || s === 'edited' || s === 'confirmed') status[f.key] = s;
  }
  return { values, status };
}

export function writeCpeData(base: Record<string, unknown>, data: CpeData): Record<string, unknown> {
  return { ...base, cpe: data.values, field_status: data.status };
}

export function isFilled(value: string | undefined): boolean {
  return value !== undefined && value.trim() !== '';
}

export function countPending(data: CpeData): { total: number; confirmed: number; ai: number } {
  const filled = ALL_FIELDS.filter((f) => isFilled(data.values[f.key]));
  return {
    total: filled.length,
    confirmed: filled.filter((f) => data.status[f.key] === 'confirmed' || data.status[f.key] === 'edited').length,
    ai: filled.filter((f) => data.status[f.key] === 'ai').length
  };
}

export function isValidCuit(value: string): boolean {
  if (!/^\d{11}$/.test(value)) return false;
  const weights = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2];
  const sum = [...value.slice(0, 10)].reduce((total, digit, index) => total + Number(digit) * weights[index], 0);
  const checkDigit = 11 - (sum % 11);
  const expected = checkDigit === 11 ? 0 : checkDigit === 10 ? 9 : checkDigit;
  return expected === Number(value[10]);
}

export function validateCpe(data: CpeData): Record<string, string> {
  const v = data.values;
  const errors: Record<string, string> = {};
  const required = [
    'requester_cuit', 'branch', 'origin_mode', 'origin_province', 'origin_locality',
    'corresponds_producer_withdrawal', 'applicant_is_field', 'grain_code', 'harvest',
    'gross_weight', 'tare_weight', 'destination_cuit', 'destination_is_field',
    'destination_province', 'destination_locality', 'recipient_cuit', 'carrier_cuit',
    'domains', 'departure', 'distance_km', 'driver_cuit', 'freight_payer_cuit', 'fumigated'
  ];
  required.forEach((key) => {
    if (!isFilled(v[key])) errors[key] = 'Este dato es obligatorio.';
  });
  const cuitKeys = [
    'requester_cuit', 'withdrawal_producer_cuit', 'role_primary_seller', 'role_secondary_seller',
    'role_secondary_seller_2', 'role_futures_market', 'role_primary_broker', 'role_secondary_broker',
    'role_delivery_representative', 'role_receiving_representative', 'destination_cuit',
    'recipient_cuit', 'carrier_cuit', 'driver_cuit', 'freight_payer_cuit', 'freight_intermediary_cuit'
  ];
  cuitKeys.forEach((key) => {
    if (isFilled(v[key]) && !isValidCuit(v[key])) errors[key] = 'Ingresá un CUIT válido de 11 dígitos.';
  });
  if (v.origin_mode === 'producer') {
    if (isFilled(v.origin_latitude) !== isFilled(v.origin_longitude)) {
      errors.origin_longitude = 'Completá latitud y longitud juntas.';
    }
    if (isFilled(v.origin_latitude) && !Number.isFinite(Number(v.origin_latitude))) errors.origin_latitude = 'Ingresá una latitud válida.';
    if (isFilled(v.origin_longitude) && !Number.isFinite(Number(v.origin_longitude))) errors.origin_longitude = 'Ingresá una longitud válida.';
    if (v.origin_latitude && (Number(v.origin_latitude) < -90 || Number(v.origin_latitude) > 90)) errors.origin_latitude = 'La latitud debe estar entre -90 y 90.';
    if (v.origin_longitude && (Number(v.origin_longitude) < -180 || Number(v.origin_longitude) > 180)) errors.origin_longitude = 'La longitud debe estar entre -180 y 180.';
  }
  if (v.origin_mode === 'operator' && !isFilled(v.origin_plant)) errors.origin_plant = 'La planta de origen es obligatoria para un operador.';
  if (v.corresponds_producer_withdrawal === 'true') {
    if (!isFilled(v.withdrawal_coe)) errors.withdrawal_coe = 'El manual exige el COE para un retiro de productor.';
    if (!isFilled(v.withdrawal_producer_cuit)) errors.withdrawal_producer_cuit = 'Indicá el remitente comercial productor.';
  }
  if (v.harvest && !/^\d{4}$/.test(v.harvest)) errors.harvest = 'La campaña debe tener cuatro dígitos (por ejemplo, 2526).';
  const gross = Number(v.gross_weight);
  const tare = Number(v.tare_weight);
  if (v.gross_weight && (!Number.isInteger(gross) || gross < 0 || gross > 88000)) errors.gross_weight = 'El peso bruto debe ser entero entre 0 y 88.000 kg.';
  if (v.tare_weight && (!Number.isInteger(tare) || tare < 0 || tare > 88000)) errors.tare_weight = 'El peso tara debe ser entero entre 0 y 88.000 kg.';
  if (v.gross_weight && v.tare_weight && gross < tare) errors.gross_weight = 'El peso bruto no puede ser menor que la tara.';
  const domains = (v.domains ?? '').split(/[\n,;]+/).map((domain) => domain.trim()).filter(Boolean);
  if (domains.length < 1 || domains.length > 3) errors.domains = 'Ingresá entre uno y tres dominios.';
  if (domains.some((domain) => !/^[a-zA-Z0-9]{6,7}$/.test(domain))) errors.domains = 'Cada dominio debe tener 6 o 7 caracteres alfanuméricos.';
  if (v.distance_km && (!/^\d+$/.test(v.distance_km) || Number(v.distance_km) < 1 || Number(v.distance_km) > 99999)) errors.distance_km = 'Los kilómetros deben ser un entero entre 1 y 99.999.';
  if (v.turn_code && !/^[A-Za-z0-9 _/-]{1,30}$/.test(v.turn_code)) errors.turn_code = 'El código admite hasta 30 caracteres alfanuméricos, espacios, guion, guion bajo y barra.';
  if (v.fare && (!/^\d{1,5}(\.\d{1,2})?$/.test(v.fare) || Number(v.fare) > 99999.99)) errors.fare = 'La tarifa admite hasta 5 dígitos enteros y 2 decimales.';
  if (v.observations && v.observations.length > 2000) errors.observations = 'El máximo es 2.000 caracteres.';
  return errors;
}
