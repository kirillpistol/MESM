"""Создать профиль и пустые CSV-контракты для другого города без чужих чисел."""
import argparse,csv,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from mesm.data.intake import DATASET_SPECS

def create_profile(name,oktmo,region,target):
    if not name.strip() or not (oktmo.isascii() and oktmo.isdigit() and len(oktmo) in (8,11)):
        raise ValueError("Нужны название и ОКТМО из 8 или 11 цифр; официальный код проверяется отдельно")
    target=Path(target)
    target.mkdir(parents=True,exist_ok=True)
    profile=target/"municipality_profile.json"
    if profile.exists(): raise FileExistsError("Профиль уже существует")
    profile.write_text(json.dumps({"municipality_name":name,"oktmo":oktmo,"region_name":region,"profile_status":"requires_identity_verification","local_norms_require_verification":True},ensure_ascii=False,indent=2),encoding="utf-8")
    for key,spec in DATASET_SPECS.items():
        path=target/f"{key}.csv"
        if path.exists(): continue
        with path.open("w",encoding="utf-8-sig",newline="") as out:
            csv.writer(out).writerow([*spec.required_columns,*spec.optional_columns])
    return profile
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--name",required=True);p.add_argument("--oktmo",required=True);p.add_argument("--region",required=True);p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();print(create_profile(a.name,a.oktmo,a.region,a.output))
