import { ALL_FIELDS, CPE_HEADER_FIELDS, CPE_SECTIONS, countPending, isFilled } from './cpeFields';
import type { CpeData, FieldDef, FieldStatus } from './cpeFields';

interface Props {
  data: CpeData;
  onChange: (data: CpeData) => void;
  readOnly?: boolean;
}

const STATUS_LABEL: Record<FieldStatus, string> = {
  ai: 'Sugerido por IA',
  edited: 'Editado',
  confirmed: 'Confirmado'
};

export function CpeForm({ data, onChange, readOnly = false }: Props) {
  function setValue(key: string, value: string) {
    const prev = data.status[key];
    const status = { ...data.status };
    if (prev === 'ai' || prev === 'confirmed') status[key] = 'edited';
    onChange({ values: { ...data.values, [key]: value }, status });
  }

  function confirm(key: string) {
    onChange({ ...data, status: { ...data.status, [key]: 'confirmed' } });
  }

  function confirmAll() {
    const status = { ...data.status };
    for (const f of ALL_FIELDS) {
      if (isFilled(data.values[f.key])) status[f.key] = 'confirmed';
    }
    onChange({ ...data, status });
  }

  const counts = countPending(data);
  const pct = counts.total ? Math.round((counts.confirmed / counts.total) * 100) : 0;

  function renderField(f: FieldDef) {
    const value = data.values[f.key] ?? '';
    const st = data.status[f.key];
    const id = `cpe-${f.key}`;
    const common = {
      id,
      value,
      disabled: readOnly,
      onChange: (e: { target: { value: string } }) => setValue(f.key, e.target.value)
    };
    return (
      <div key={f.key} className={`cpe-field${f.wide ? ' wide' : ''}${st ? ` st-${st}` : ''}`}>
        <div className="cpe-field-head">
          <label htmlFor={id}>{f.label}{f.unit ? ` (${f.unit})` : ''}</label>
          {st && <span className={`badge badge-${st}`}>{STATUS_LABEL[st]}</span>}
        </div>
        {f.type === 'select' ? (
          <select {...common}>
            <option value="">—</option>
            {f.options!.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
        ) : f.type === 'textarea' ? (
          <textarea {...common} rows={2} />
        ) : (
          <input {...common} type={f.type ?? 'text'} />
        )}
        {!readOnly && st === 'ai' && isFilled(value) && (
          <button type="button" className="btn-link" onClick={() => confirm(f.key)}>
            Confirmar dato
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="cpe-form">
      <div className="cpe-progress">
        <div>
          <strong>Validación:</strong> {counts.confirmed} de {counts.total} campos revisados
          {counts.ai > 0 && <span className="badge badge-ai">{counts.ai} pendientes de IA</span>}
          <div className="bar"><span style={{ width: `${pct}%` }} /></div>
        </div>
        {!readOnly && (
          <button type="button" className="btn-secondary" onClick={confirmAll}>
            Confirmar todos
          </button>
        )}
      </div>

      <section className="cpe-section">
        <h3><span className="sec-id">#</span> Cabecera</h3>
        <div className="cpe-fields">{CPE_HEADER_FIELDS.map(renderField)}</div>
      </section>

      {CPE_SECTIONS.map((s) => (
        <section key={s.id} className="cpe-section">
          <h3><span className="sec-id">{s.id}</span> {s.title}</h3>
          <div className="cpe-fields">{s.fields.map(renderField)}</div>
        </section>
      ))}
    </div>
  );
}
