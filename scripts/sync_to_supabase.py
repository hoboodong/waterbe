#!/usr/bin/env python3
"""
워터비 YAML 데이터를 Supabase github_* 테이블로 임포트
GitHub Actions용 - 환경변수에서 Supabase 설정 읽음
"""
import yaml
import sys
import os
import requests
from pathlib import Path

# Supabase 설정 (환경변수에서 읽기)
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ SUPABASE_URL and SUPABASE_KEY environment variables required")
    sys.exit(1)

# 매장별 store_id 매핑
STORE_MAP = {
    "store_wangsimni": "wangsimni",
    "store_mapo": "mapo",
    "store_wolgye": "wolgye"
}

def get_waterbe_path():
    """워터비 데이터 경로 결정 (GitHub Actions or 로컬)"""
    # GitHub Actions에서는 repo root
    if os.environ.get('GITHUB_ACTIONS'):
        return Path('instances/master')
    # 로컬에서는 기존 경로
    return Path.home() / ".openclaw" / "shared" / "waterbe" / "instances" / "master"

def load_yaml(path: Path):
    """YAML 파일 로드"""
    with open(path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data.get('instances', data.get('entities', []))

def supabase_request(method: str, table: str, data=None, params=None):
    """Supabase REST API 요청"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates"
    }

    response = requests.request(method, url, headers=headers, json=data, params=params)
    response.raise_for_status()
    return response

def import_ingredients():
    """재료 임포트"""
    waterbe_path = get_waterbe_path()
    ingredients_file = waterbe_path / "ingredients.yaml"

    if not ingredients_file.exists():
        print(f"❌ Ingredients file not found: {ingredients_file}")
        return

    ingredients = load_yaml(ingredients_file)
    print(f"📦 Found {len(ingredients)} ingredients")

    success_count = 0
    error_count = 0

    for ing in ingredients:
        ing_id = ing['id']
        data = ing['data']

        row = {
            'id': ing_id,
            'name': data.get('name'),
            'origin': data.get('origin'),
            'allergens': data.get('allergens', []),
            'ratio': data.get('ratio'),
        }

        try:
            supabase_request('POST', 'github_ingredients', data=row)
            print(f"✅ {row['name']}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to import {ing_id}: {e}")
            error_count += 1

    print(f"\n🎉 Ingredients: {success_count} success, {error_count} errors")

def import_products():
    """상품 임포트"""
    waterbe_path = get_waterbe_path()
    products_file = waterbe_path / "products.yaml"

    if not products_file.exists():
        print(f"❌ Products file not found: {products_file}")
        return

    products = load_yaml(products_file)
    print(f"📦 Found {len(products)} products")

    success_count = 0
    error_count = 0

    for prod in products:
        prod_id = prod['id']
        data = prod['data']

        row = {
            'id': prod_id,
            'name': data.get('name'),
            'category': data.get('category'),
            'base_price': data.get('basePrice'),
            'description': data.get('description'),
        }

        try:
            supabase_request('POST', 'github_products', data=row)
            print(f"✅ {row['name']}")
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to import {prod_id}: {e}")
            error_count += 1

    print(f"\n🎉 Products: {success_count} success, {error_count} errors")

def import_recipes(store_key: str = None):
    """레시피 임포트"""
    waterbe_path = get_waterbe_path()
    recipes_path = waterbe_path / "recipes"

    # 임포트할 매장 결정
    if store_key:
        store_id = STORE_MAP.get(store_key)
        if not store_id:
            print(f"❌ Unknown store: {store_key}")
            return
        recipe_files = [(store_id, recipes_path / f"{store_id}.yaml")]
    else:
        # 전체 매장
        recipe_files = [
            ("wangsimni", recipes_path / "wangsimni.yaml"),
            ("mapo", recipes_path / "mapo.yaml"),
            ("wolgye", recipes_path / "wolgye.yaml"),
        ]

    # 재료 이름 매핑
    ingredients_file = waterbe_path / "ingredients.yaml"
    ingredients = load_yaml(ingredients_file)
    ingredient_map = {ing['id']: ing['data']['name'] for ing in ingredients}

    total_success = 0
    total_error = 0

    for store_id, recipe_file in recipe_files:
        if not recipe_file.exists():
            print(f"❌ Recipe file not found: {recipe_file}")
            continue

        recipes = load_yaml(recipe_file)
        print(f"\n📦 Found {len(recipes)} recipes for {store_id}")

        success_count = 0
        error_count = 0

        for recipe in recipes:
            recipe_id = recipe['id']
            data = recipe['data']
            relations = recipe.get('relations', {})

            # Recipe 레코드 준비
            recipe_row = {
                'id': recipe_id,
                'name': data['name'],
                'price': data.get('price'),
                'effective_from': data.get('effectiveFrom'),
                'effective_to': data.get('effectiveTo'),
                'product_id': relations.get('forProduct'),
                'store_id': store_id,
                'mart_code': data.get('martCode'),
            }

            try:
                # Recipe INSERT (UPSERT)
                supabase_request('POST', 'github_recipes', data=recipe_row)

                # 기존 재료 삭제
                supabase_request('DELETE', 'github_recipe_ingredients',
                               params={'recipe_id': f'eq.{recipe_id}'})

                # Recipe ingredients INSERT
                uses = relations.get('uses', [])
                ingredient_rows = []
                for idx, use in enumerate(uses):
                    ingredient_id = use.get('ingredient')
                    ingredient_name = ingredient_map.get(ingredient_id, ingredient_id)

                    ingredient_rows.append({
                        'recipe_id': recipe_id,
                        'ingredient_id': ingredient_id,
                        'ingredient_name': ingredient_name,
                        'amount': use.get('amount'),
                        'unit': use.get('unit'),
                        'pspec_id': use.get('pspec'),
                        'sequence': idx,
                    })

                if ingredient_rows:
                    supabase_request('POST', 'github_recipe_ingredients', data=ingredient_rows)

                print(f"  ✅ {recipe_row['name']} ({len(uses)} ingredients)")
                success_count += 1

            except Exception as e:
                print(f"  ❌ Failed to import {recipe_id}: {e}")
                error_count += 1

        print(f"📊 {store_id}: {success_count} success, {error_count} errors")
        total_success += success_count
        total_error += error_count

    print(f"\n🎉 Total: {total_success} success, {total_error} errors")

def main():
    """전체 임포트"""
    print("🚀 워터비 데이터 → Supabase github_* 테이블 임포트 시작\n")

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "ingredients":
            import_ingredients()
        elif command == "products":
            import_products()
        elif command == "recipes":
            store_key = sys.argv[2] if len(sys.argv) > 2 else None
            import_recipes(store_key)
        elif command == "all":
            import_ingredients()
            print("\n" + "="*60 + "\n")
            import_products()
            print("\n" + "="*60 + "\n")
            import_recipes()
        else:
            print(f"❌ Unknown command: {command}")
            print("Usage: python sync_to_supabase.py [ingredients|products|recipes|all]")
    else:
        # 기본: 전체 임포트
        import_ingredients()
        print("\n" + "="*60 + "\n")
        import_products()
        print("\n" + "="*60 + "\n")
        import_recipes()

if __name__ == "__main__":
    main()
