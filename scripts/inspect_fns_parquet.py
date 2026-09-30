"""Проверка реального Parquet и извлечение строк Сургута без загрузки всей страны в память."""
import argparse
import hashlib
import json
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('file')
    parser.add_argument('--output', default='data/external/fns_5ndfl_surgut.csv')
    args = parser.parse_args()
    parquet = pq.ParquetFile(args.file)
    required = {'object_oktmo', 'indicator_name', 'indicator_value', 'year', 'report_date'}
    if not required <= set(parquet.schema.names):
        raise ValueError('Схема 5-НДФЛ изменилась')
    batches = []
    for batch in parquet.iter_batches(batch_size=65536):
        mask = pc.equal(batch.column('object_name'), 'Сургут')
        filtered = batch.filter(mask)
        if filtered.num_rows: batches.append(filtered)
    if not batches:
        raise ValueError('Нет точного совпадения названия Сургут; нужна проверка ОКТМО')
    table = pa.Table.from_batches(batches)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    table.to_pandas().to_csv(output, index=False)
    digest = hashlib.sha256(Path(args.file).read_bytes()).hexdigest()
    registry_path = Path('config/external_sources.json')
    registry = json.loads(registry_path.read_text())
    source = next(s for s in registry['external_sources'] if s['id'] == 'fns_5ndfl')
    source.update(artifact_sha256=digest, oktmo_field='object_oktmo', extracted_file=str(output),
                  actual_rows=parquet.metadata.num_rows,
                  blocker='Схема проверена; требуется выбор показателя, разреза, проверка ОКТМО и дат публикации. report_date не считается available_at автоматически.')
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2)+'\n')
    from mesm.sources.registry import transition
    if source['status'] == 'candidate':
        transition(registry_path, 'fns_5ndfl', 'connected', actor='kirill', evidence='Получен реальный файл, проверены обязательные поля, записана SHA256 и выгрузка Сургута')
    print(table.num_rows, digest)
