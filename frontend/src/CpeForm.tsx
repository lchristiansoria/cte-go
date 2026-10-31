import { useEffect, useMemo, useState } from 'react';
import { api } from './api';
import { isFilled, validateCpe } from './cpeFields';
import type { CpeData } from './cpeFields';
import type { Client } from './types';

interface CatalogItem {
  codigo: string;
  descripcion: string;
  reference?: string;
  provinceCode?: string;
  localityCode?: string;
}

interface Props {
  data: CpeData;
  clients: Client[];
  token: string;
  onChange: (data: CpeData) => void;
  readOnly?: boolean;
  showErrors?: boolean;
  serverErrors?: Record<string, string>;
}

const COMMERCIAL_ROLES = [
  ['role_primary_seller', 'Remitente comercial venta primaria'],
  ['role_secondary_seller', 'Remitente comercial venta secundaria'],
  ['role_secondary_seller_2', 'Remitente comercial venta secundaria 2'],
  ['role_futures_market', 'Mercado a término'],
  ['role_primary_broker', 'Corredor venta primaria'],
  ['role_secondary_broker', 'Corredor venta secundaria'],
  ['role_delivery_representative', 'Representante entregador'],
  ['role_receiving_representative', 'Representante recibidor']
] as const;

function listFromResponse(value: unknown, keys: string[]): CatalogItem[] {
  let result = value;
  while (result && typeof result === 'object' && !Array.isArray(result) && 'respuesta' in result) {
    result = (result as Record<string, unknown>).respuesta;
  }
  if (result && typeof result === 'object' && !Array.isArray(result)) {
    const record = result as Record<string, unknown>;
    const collection = keys.map((key) => record[key]).find(Array.isArray);
    if (!collection) throw new Error('ARCA devolvió un catálogo con un formato no reconocido.');
    result = collection;
  }
  if (!Array.isArray(result)) throw new Error('ARCA devolvió un catálogo con un formato no reconocido.');
  return result.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const record = item as Record<string, unknown>;
    const code = record.codigo ?? record.codigoPlanta ?? record.nroPlanta ?? record.planta;
    const description = record.descripcion ?? record.nombre ?? (code === undefined ? record.ubicacionGeoreferencial : `Planta ${code}`);
    if (code === undefined || description === undefined) return [];
    return [{
      codigo: String(code),
      descripcion: String(description),
      reference: typeof record.domicilio === 'string'
        ? record.domicilio
        : typeof record.ubicacionGeoreferencial === 'string'
          ? record.ubicacionGeoreferencial
          : undefined,
      provinceCode: record.codProvincia === undefined ? undefined : String(record.codProvincia),
      localityCode: record.codLocalidad === undefined ? undefined : String(record.codLocalidad)
    }];
  });
}

function Field({ label, id, error, children }: {
  label: string;
  id: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className={`cpe-field${error ? ' has-error' : ''}`}>
      <label htmlFor={id}>{label}</label>
      {children}
      {error && <small className="field-error" role="alert">{error}</small>}
    </div>
  );
}

export function CpeForm({ data, clients, token, onChange, readOnly = false, showErrors = false, serverErrors = {} }: Props) {
  const [provinces, setProvinces] = useState<CatalogItem[]>([]);
  const [grains, setGrains] = useState<CatalogItem[]>([]);
  const [originLocalities, setOriginLocalities] = useState<CatalogItem[]>([]);
  const [destinationLocalities, setDestinationLocalities] = useState<CatalogItem[]>([]);
  const [plants, setPlants] = useState<CatalogItem[]>([]);
  const [catalogError, setCatalogError] = useState('');
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [defaultBranch, setDefaultBranch] = useState<number | null>(null);
  const values = data.values;
  const errors = useMemo(
    () => ({ ...(showErrors ? validateCpe(data) : {}), ...serverErrors }),
    [data, showErrors, serverErrors]
  );
  const netWeight = useMemo(() => {
    if (!isFilled(values.gross_weight) || !isFilled(values.tare_weight)) return '';
    const gross = Number(values.gross_weight);
    const tare = Number(values.tare_weight);
    return Number.isFinite(gross) && Number.isFinite(tare) ? String(gross - tare) : '';
  }, [values.gross_weight, values.tare_weight]);

  useEffect(() => {
    let active = true;
    setCatalogLoading(true);
    Promise.all([api.arcaProvinces(token), api.arcaGrains(token), api.arcaConfiguration(token)])
      .then(([provinceResponse, grainResponse, configuration]) => {
        if (!active) return;
        setProvinces(listFromResponse(provinceResponse, ['provincia', 'provincias']));
        setGrains(listFromResponse(grainResponse, ['grano', 'granos']));
        setDefaultBranch(configuration.sucursal);
        setCatalogError('');
      })
      .catch((error: unknown) => {
        if (active) setCatalogError(error instanceof Error ? error.message : 'No se pudieron cargar los catálogos ARCA.');
      })
      .finally(() => { if (active) setCatalogLoading(false); });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    if (!values.branch && defaultBranch !== null) setValue('branch', String(defaultBranch));
  }, [defaultBranch, values.branch]);

  useEffect(() => {
    let active = true;
    setOriginLocalities([]);
    if (!values.origin_province) return () => { active = false; };
    api.arcaLocalities(token, values.origin_province)
      .then((response) => { if (active) setOriginLocalities(listFromResponse(response, ['localidad', 'localidades'])); })
      .catch((error: unknown) => { if (active) setCatalogError(error instanceof Error ? error.message : 'No se pudieron cargar las localidades.'); });
    return () => { active = false; };
  }, [token, values.origin_province]);

  useEffect(() => {
    let active = true;
    setDestinationLocalities([]);
    if (!values.destination_province) return () => { active = false; };
    api.arcaLocalities(token, values.destination_province)
      .then((response) => { if (active) setDestinationLocalities(listFromResponse(response, ['localidad', 'localidades'])); })
      .catch((error: unknown) => { if (active) setCatalogError(error instanceof Error ? error.message : 'No se pudieron cargar las localidades.'); });
    return () => { active = false; };
  }, [token, values.destination_province]);

  useEffect(() => {
    let active = true;
    setPlants([]);
    if (!values.destination_cuit) return () => { active = false; };
    api.arcaPlants(token, values.destination_cuit)
      .then((response) => { if (active) setPlants(listFromResponse(response, ['planta', 'plantas'])); })
      .catch((error: unknown) => {
        if (!active) return;
        setPlants([]);
        setCatalogError(error instanceof Error ? error.message : 'No se pudo consultar el catálogo de plantas.');
      });
    return () => { active = false; };
  }, [token, values.destination_cuit]);

  function setValue(key: string, value: string, displayLabel?: string) {
    const status = { ...data.status };
    if (status[key] === 'ai' || status[key] === 'confirmed') status[key] = 'edited';
    const next = { ...values, [key]: value };
    const labelKey: Record<string, string> = {
      grain_code: 'grain_label',
      origin_province: 'origin_province_label',
      origin_locality: 'origin_locality_label',
      destination_province: 'destination_province_label',
      destination_locality: 'destination_locality_label',
      destination_plant: 'destination_plant_label'
    };
    if (labelKey[key]) {
      if (displayLabel) next[labelKey[key]] = displayLabel;
      else delete next[labelKey[key]];
    }
    if (key === 'origin_mode') {
      delete next.origin_province;
      delete next.origin_province_label;
      delete next.origin_locality;
      delete next.origin_locality_label;
      delete next.origin_plant;
      delete next.origin_renspa;
      delete next.origin_latitude;
      delete next.origin_longitude;
    }
    if (key === 'origin_province') {
      delete next.origin_locality;
      delete next.origin_locality_label;
    }
    if (key === 'destination_province') {
      delete next.destination_locality;
      delete next.destination_locality_label;
      delete next.destination_plant;
      delete next.destination_plant_label;
    }
    if (key === 'destination_locality') {
      delete next.destination_plant;
      delete next.destination_plant_label;
    }
    if (key === 'destination_cuit') {
      delete next.destination_plant;
      delete next.destination_plant_label;
    }
    onChange({ values: next, status });
  }

  function input(key: string, label: string, type = 'text', options?: { min?: string; max?: string; step?: string; maxLength?: number }) {
    const id = `cpe-${key}`;
    return (
      <Field key={key} id={id} label={label} error={errors[key]}>
        <input
          id={id}
          type={type}
          value={values[key] ?? ''}
          disabled={readOnly}
          min={options?.min}
          max={options?.max}
          step={options?.step}
          maxLength={options?.maxLength}
          aria-invalid={!!errors[key]}
          onChange={(event) => setValue(key, event.target.value)}
        />
      </Field>
    );
  }

  function catalogSelect(
    key: string,
    label: string,
    entries: CatalogItem[],
    placeholder = 'Seleccioná una opción'
  ) {
    const id = `cpe-${key}`;
    return (
      <Field key={key} id={id} label={label} error={errors[key]}>
        <select
          id={id}
          value={values[key] ?? ''}
          disabled={readOnly || catalogLoading}
          aria-invalid={!!errors[key]}
          onChange={(event) => {
            const selected = entries.find((entry) => entry.codigo === event.target.value);
            setValue(key, event.target.value, selected?.descripcion);
          }}
        >
          <option value="">{placeholder}</option>
          {entries.map((entry) => <option key={entry.codigo} value={entry.codigo}>{entry.descripcion} · {entry.codigo}</option>)}
        </select>
      </Field>
    );
  }

  function companySelect(key: string, label: string) {
    const id = `cpe-${key}`;
    return (
      <Field key={key} id={id} label={label} error={errors[key]}>
        <select id={id} value={values[key] ?? ''} disabled={readOnly} aria-invalid={!!errors[key]} onChange={(event) => setValue(key, event.target.value)}>
          <option value="">Seleccioná una empresa</option>
          {clients.map((client) => <option key={`${key}-${client.id}`} value={client.cuit}>{client.business_name} · CUIT {client.cuit}</option>)}
        </select>
        {values[key] && clients.find((client) => client.cuit === values[key]) && (
          <small>{clients.find((client) => client.cuit === values[key])?.business_name}</small>
        )}
      </Field>
    );
  }

  function selectPlant(plant: CatalogItem | undefined) {
    const next = { ...values };
    if (!plant) {
      delete next.destination_plant;
      delete next.destination_plant_label;
    } else {
      next.destination_plant = plant.codigo;
      next.destination_plant_label = plant.descripcion;
      if (plant.provinceCode) {
        next.destination_province = plant.provinceCode;
        const province = provinces.find((item) => item.codigo === plant.provinceCode);
        if (province) next.destination_province_label = province.descripcion;
      }
      if (plant.localityCode) {
        next.destination_locality = plant.localityCode;
        const locality = values.destination_province === plant.provinceCode
          ? destinationLocalities.find((item) => item.codigo === plant.localityCode)
          : undefined;
        if (locality) next.destination_locality_label = locality.descripcion;
        else delete next.destination_locality_label;
      }
    }
    onChange({ values: next, status: { ...data.status } });
  }

  function booleanSelect(key: string, label: string, yes: string, no: string) {
    const id = `cpe-${key}`;
    return (
      <Field key={key} id={id} label={label} error={errors[key]}>
        <select id={id} value={values[key] ?? ''} disabled={readOnly} aria-invalid={!!errors[key]} onChange={(event) => setValue(key, event.target.value)}>
          <option value="">Seleccioná una respuesta</option>
          <option value="true">{yes}</option>
          <option value="false">{no}</option>
        </select>
      </Field>
    );
  }

  const originMode = values.origin_mode;
  const destinationReference = plants.find((plant) => plant.codigo === values.destination_plant)?.reference;

  return (
    <div className="cpe-form">
      {catalogError && <p className="error" role="alert">No se pudieron cargar todos los catálogos ARCA: {catalogError}</p>}
      {catalogLoading && <p role="status">Cargando catálogos oficiales…</p>}
      <section className="cpe-section">
        <h3>Datos de la carta</h3>
        <div className="cpe-fields">
          {companySelect('requester_cuit', 'Solicitante/titular')}
          {input('branch', 'Sucursal', 'number', { min: '1', max: '99999', step: '1' })}
          <p className="cpe-note">El tipo es Carta de Porte Automotor (código 74). El número de orden se consulta a ARCA al emitir; no se calcula localmente.</p>
        </div>
      </section>

      <section className="cpe-section">
        <h3>Origen / procedencia</h3>
        <div className="cpe-fields">
          <Field id="cpe-origin_mode" label="Modalidad del origen" error={errors.origin_mode}>
            <select id="cpe-origin_mode" value={originMode ?? ''} disabled={readOnly} onChange={(event) => setValue('origin_mode', event.target.value)}>
              <option value="">Seleccioná modalidad</option>
              <option value="producer">Productor</option>
              <option value="operator">Operador / planta</option>
            </select>
          </Field>
          {originMode && <>
            {catalogSelect('origin_province', 'Provincia', provinces)}
            {catalogSelect('origin_locality', 'Localidad', originLocalities, values.origin_province ? 'Seleccioná localidad' : 'Primero seleccioná provincia')}
          </>}
          {originMode === 'operator' && input('origin_plant', 'Planta de origen', 'number', { min: '1', max: '999999', step: '1' })}
          {originMode === 'producer' && <>
            {input('origin_renspa', 'RENSPA (opcional)', 'text', { maxLength: 30 })}
            {input('origin_latitude', 'Latitud decimal (opcional)', 'number', { min: '-90', max: '90', step: 'any' })}
            {input('origin_longitude', 'Longitud decimal (opcional)', 'number', { min: '-180', max: '180', step: 'any' })}
          </>}
          {booleanSelect('corresponds_producer_withdrawal', '¿Corresponde retiro del productor?', 'Sí', 'No')}
          {booleanSelect('applicant_is_field', '¿El solicitante es de campo?', 'Sí', 'No')}
          {values.corresponds_producer_withdrawal === 'true' && <>
            {input('withdrawal_coe', 'Número COE del certificado de retiro', 'number', { min: '1', step: '1' })}
            {companySelect('withdrawal_producer_cuit', 'Remitente comercial productor')}
          </>}
        </div>
      </section>

      <section className="cpe-section">
        <h3>Intervinientes comerciales (opcionales según operación)</h3>
        <div className="cpe-fields">{COMMERCIAL_ROLES.map(([key, label]) => companySelect(key, label))}</div>
        <p className="cpe-note">El manual define estos roles como opcionales. Una empresa puede ocupar más de un rol. El remitente productor se informa en el bloque de retiro cuando corresponde.</p>
      </section>

      <section className="cpe-section">
        <h3>Carga</h3>
        <div className="cpe-fields">
          {catalogSelect('grain_code', 'Grano / especie', grains)}
          {input('harvest', 'Cosecha / campaña (4 dígitos)', 'text', { maxLength: 4 })}
          {input('gross_weight', 'Peso bruto (kg)', 'number', { min: '0', max: '88000', step: '1' })}
          {input('tare_weight', 'Peso tara (kg)', 'number', { min: '0', max: '88000', step: '1' })}
          <Field id="cpe-net-weight" label="Peso neto calculado (kg)">
            <input id="cpe-net-weight" value={netWeight} readOnly aria-readonly="true" />
          </Field>
        </div>
      </section>

      <section className="cpe-section">
        <h3>Destino físico y destinatario</h3>
        <div className="cpe-fields">
          {companySelect('destination_cuit', 'Destino físico · CUIT')}
          {booleanSelect('destination_is_field', '¿El destino es un campo?', 'Sí', 'No, es una planta')}
          {catalogSelect('destination_province', 'Provincia del destino', provinces)}
          {catalogSelect('destination_locality', 'Localidad del destino', destinationLocalities, values.destination_province ? 'Seleccioná localidad' : 'Primero seleccioná provincia')}
          {plants.length > 0 && (
            <Field id="cpe-destination_plant" label="Planta de destino (opcional según esquema)" error={errors.destination_plant}>
              <select
                id="cpe-destination_plant"
                value={values.destination_plant ?? ''}
                disabled={readOnly || !plants.length}
                onChange={(event) => {
                  const selected = plants.find((plant) => plant.codigo === event.target.value);
                  selectPlant(selected);
                }}
              >
                <option value="">{plants.length ? 'Seleccioná una planta' : 'Sin establecimientos disponibles'}</option>
                {plants.map((plant) => <option key={plant.codigo} value={plant.codigo}>{plant.descripcion} · {plant.codigo}</option>)}
              </select>
              {destinationReference && <small>Ubicación de referencia: {destinationReference}</small>}
            </Field>
          )}
          {plants.length === 0 && input('destination_plant', 'Código de planta de destino (opcional)', 'number', { min: '1', max: '999999', step: '1' })}
          {companySelect('recipient_cuit', 'Destinatario · CUIT')}
        </div>
      </section>

      <section className="cpe-section">
        <h3>Transporte</h3>
        <div className="cpe-fields">
          {companySelect('carrier_cuit', 'Transportista')}
          <Field id="cpe-domains" label="Patentes / dominios (uno por línea)" error={errors.domains}>
            <textarea id="cpe-domains" value={values.domains ?? ''} disabled={readOnly} rows={3} placeholder="Ej.: AJV636&#10;GRP753" aria-invalid={!!errors.domains} onChange={(event) => setValue('domains', event.target.value.toUpperCase())} />
          </Field>
          {input('departure', 'Fecha y hora de partida (hora de Argentina, UTC−03:00)', 'datetime-local', { step: '60' })}
          {input('distance_km', 'Kilómetros a recorrer', 'number', { min: '1', max: '99999', step: '1' })}
          {input('turn_code', 'Código de turno (opcional)', 'text', { maxLength: 30 })}
          {companySelect('driver_cuit', 'Chofer')}
          {input('fare', 'Tarifa informada (máx. 5 enteros y 2 decimales)', 'number', { min: '0', max: '99999.99', step: '0.01' })}
          <p className="cpe-note">El manual no especifica moneda ni unidad para la tarifa; no se interpreta como total de viaje.</p>
          {companySelect('freight_payer_cuit', 'Pagador del flete')}
          {companySelect('freight_intermediary_cuit', 'Intermediario del flete (opcional)')}
          {booleanSelect('fumigated', '¿La mercadería fue fumigada?', 'Sí, fue fumigada', 'No fue fumigada')}
        </div>
      </section>

      <section className="cpe-section">
        <h3>Observaciones</h3>
        <div className="cpe-fields">
          <Field id="cpe-observations" label="Observaciones (máximo 2.000 caracteres)" error={errors.observations}>
            <textarea id="cpe-observations" value={values.observations ?? ''} disabled={readOnly} rows={3} maxLength={2000} onChange={(event) => setValue('observations', event.target.value)} />
          </Field>
        </div>
      </section>
    </div>
  );
}
