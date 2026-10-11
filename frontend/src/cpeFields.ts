export type FieldStatus = 'ai' | 'edited' | 'confirmed';

export interface FieldDef {
  key: string;
  label: string;
  type?: 'text' | 'number' | 'date' | 'datetime-local' | 'select' | 'textarea';
  options?: string[];
  wide?: boolean;
  unit?: string;
}

export interface SectionDef {
  id: string;
  title: string;
  fields: FieldDef[];
}

export const CPE_HEADER_FIELDS: FieldDef[] = [
  { key: 'ctg', label: 'CTG' },
  { key: 'nro_cpe', label: 'N° CPE' },
  { key: 'fecha', label: 'Fecha', type: 'date' },
  { key: 'vencimiento', label: 'Vencimiento', type: 'datetime-local' }
];

export const CPE_SECTIONS: SectionDef[] = [
  {
    id: 'A',
    title: 'Intervinientes',
    fields: [
      { key: 'titular', label: 'Titular carta de porte' },
      { key: 'rte_productor', label: 'Remitente comercial productor' },
      { key: 'rte_venta_primaria', label: 'Rte. comercial venta primaria' },
      { key: 'rte_venta_secundaria', label: 'Rte. comercial venta secundaria' },
      { key: 'rte_venta_secundaria_2', label: 'Rte. comercial venta secundaria 2' },
      { key: 'mercado_termino', label: 'Mercado a término' },
      { key: 'corredor_primaria', label: 'Corredor venta primaria' },
      { key: 'corredor_secundaria', label: 'Corredor venta secundaria' },
      { key: 'representante_entregador', label: 'Representante entregador' },
      { key: 'representante_recibidor', label: 'Representante recibidor' },
      { key: 'destinatario', label: 'Destinatario' },
      { key: 'destino', label: 'Destino' },
      { key: 'transportista', label: 'Empresa transportista' },
      { key: 'chofer', label: 'Chofer' },
      { key: 'flete_pagador', label: 'Flete pagador' },
      { key: 'intermediario_flete', label: 'Intermediario de flete' }
    ]
  },
  {
    id: 'B',
    title: 'Grano / Especie',
    fields: [
      { key: 'grano', label: 'Grano' },
      { key: 'tipo', label: 'Tipo' },
      { key: 'campana', label: 'Campaña' },
      { key: 'calidad', label: 'Declaración de calidad', type: 'select', options: ['Conforme', 'Condicional'] },
      { key: 'peso_bruto', label: 'Peso bruto', type: 'number', unit: 'kg' },
      { key: 'peso_tara', label: 'Peso tara', type: 'number', unit: 'kg' },
      { key: 'peso_neto', label: 'Peso neto', type: 'number', unit: 'kg' },
      { key: 'observaciones', label: 'Observaciones', type: 'textarea', wide: true }
    ]
  },
  {
    id: 'C',
    title: 'Procedencia',
    fields: [
      { key: 'proc_localidad', label: 'Localidad' },
      { key: 'proc_provincia', label: 'Provincia' },
      { key: 'proc_es_campo', label: 'Es un campo', type: 'select', options: ['Si', 'No'] },
      { key: 'proc_renspa', label: 'RENSPA' },
      { key: 'proc_latitud', label: 'Latitud' },
      { key: 'proc_longitud', label: 'Longitud' },
      { key: 'proc_descripcion', label: 'Descripción' }
    ]
  },
  {
    id: 'D',
    title: 'Destino de la mercadería',
    fields: [
      { key: 'dest_planta', label: 'N° planta' },
      { key: 'dest_localidad', label: 'Localidad' },
      { key: 'dest_provincia', label: 'Provincia' },
      { key: 'dest_direccion', label: 'Dirección' },
      { key: 'dest_es_campo', label: 'Es un campo', type: 'select', options: ['Si', 'No'] }
    ]
  },
  {
    id: 'E',
    title: 'Datos del transporte',
    fields: [
      { key: 'dominios', label: 'Dominios' },
      { key: 'kms', label: 'Kms a recorrer', type: 'number', unit: 'km' },
      { key: 'partida', label: 'Fecha y hora de partida', type: 'datetime-local' },
      { key: 'tarifa', label: 'Tarifa', type: 'number' },
      { key: 'tarifa_referencia', label: 'Tarifa de referencia', type: 'number' }
    ]
  },
  {
    id: 'F',
    title: 'Contingencias',
    fields: [
      { key: 'contingencia', label: 'Contingencia' },
      { key: 'contingencia_otro', label: 'Otro' },
      { key: 'desactivacion', label: 'Desactivación' },
      { key: 'desactivacion_otro', label: 'Otro (desactivación)' }
    ]
  },
  {
    id: 'G',
    title: 'Descarga',
    fields: [
      { key: 'desc_fecha', label: 'Fecha descarga', type: 'datetime-local' },
      { key: 'desc_arribo', label: 'Fecha arribo', type: 'datetime-local' },
      { key: 'desc_turno', label: 'N° turno' },
      { key: 'desc_peso_bruto', label: 'Peso bruto', type: 'number', unit: 'kg' },
      { key: 'desc_peso_tara', label: 'Peso tara', type: 'number', unit: 'kg' },
      { key: 'desc_peso_neto', label: 'Peso neto', type: 'number', unit: 'kg' },
      { key: 'desc_localidad', label: 'Localidad' },
      { key: 'desc_provincia', label: 'Provincia' }
    ]
  }
];

export const ALL_FIELDS: FieldDef[] = [...CPE_HEADER_FIELDS, ...CPE_SECTIONS.flatMap((s) => s.fields)];

export interface CpeData {
  values: Record<string, string>;
  status: Record<string, FieldStatus>;
}

export function readCpeData(payload: Record<string, unknown>): CpeData {
  const rawValues = (payload.cpe ?? {}) as Record<string, unknown>;
  const rawStatus = (payload.field_status ?? {}) as Record<string, unknown>;
  const values: Record<string, string> = {};
  const status: Record<string, FieldStatus> = {};
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

export function isFilled(v: string | undefined): boolean {
  return !!v && v.trim() !== '';
}

export function countPending(data: CpeData): { total: number; confirmed: number; ai: number } {
  const filled = ALL_FIELDS.filter((f) => isFilled(data.values[f.key]));
  return {
    total: filled.length,
    confirmed: filled.filter((f) => data.status[f.key] === 'confirmed' || data.status[f.key] === 'edited').length,
    ai: filled.filter((f) => data.status[f.key] === 'ai').length
  };
}
