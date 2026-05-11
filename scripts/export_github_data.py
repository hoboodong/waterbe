#!/usr/bin/env python3
"""
Supabase github_* 테이블 데이터를 워터비 YAML로 export
"""
import yaml
import requests
import os
import base64
from pathlib import Path
from typing import Dict, List, Any

# Supabase 설정
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://uvlmxspvgaagqaisdvhj.supabase.co')
SUPABASE_KEY = os.environ.get('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV2bG14c3B2Z2FhZ3FhaXNkdmhqIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc2ODgwODksImV4cCI6MjA5MzI2NDA4OX0.EhZskFp8ci0Mk-VypHHW1wxrW8obC63UE1akOApmKnE')

# GitHub 설정
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN')
GITHUB_REPO = 'hoboodong/waterbe'
GITHUB_API = 'https://api.github.com'

def supabase_get(table: str, params: Dict = None) -> List[Dict]:
    """Supabase에서 데이터 읽기"""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

def export_ingredients() -> Dict:
    """재료 데이터 export"""
    ingredients = supabase_get('github_ingredients')

    instances = []
    for ing in ingredients:
        instance = {
            'id': ing['id'],
            'class': 'Ingredient',
            'data': {
                'name': ing['name'],
            }
        }

        if ing.get('origin'):
            instance['data']['origin'] = ing['origin']
        if ing.get('allergens'):
            instance['data']['allergens'] = ing['allergens']
        if ing.get('ratio'):
            instance['data']['ratio'] = float(ing['ratio'])

        instances.append(instance)

    return {'instances': instances}

def export_products() -> Dict:
    """상품 데이터 export"""
    products = supabase_get('github_products')

    instances = []
    for prod in products:
        instance = {
            'id': prod['id'],
            'class': 'Product',
            'data': {
                'name': prod['name'],
            }
        }

        if prod.get('category'):
            instance['data']['category'] = prod['category']
        if prod.get('base_price'):
            instance['data']['basePrice'] = prod['base_price']
        if prod.get('description'):
            instance['data']['description'] = prod['description']

        instances.append(instance)

    return {'instances': instances}

def export_recipes(store_id: str) -> Dict:
    """레시피 데이터 export (매장별)"""
    # 레시피 읽기
    recipes = supabase_get('github_recipes', params={'store_id': f'eq.{store_id}'})

    instances = []
    for recipe in recipes:
        recipe_id = recipe['id']

        # 레시피 재료 읽기
        ingredients = supabase_get('github_recipe_ingredients',
                                  params={'recipe_id': f'eq.{recipe_id}',
                                         'order': 'sequence.asc'})

        instance = {
            'id': recipe_id,
            'class': 'Recipe',
            'data': {
                'name': recipe['name'],
            },
            'relations': {}
        }

        # 선택적 필드
        if recipe.get('price'):
            instance['data']['price'] = recipe['price']
        if recipe.get('effective_from'):
            instance['data']['effectiveFrom'] = str(recipe['effective_from'])
        if recipe.get('effective_to'):
            instance['data']['effectiveTo'] = str(recipe['effective_to'])
        if recipe.get('mart_code'):
            instance['data']['martCode'] = recipe['mart_code']

        # Relations
        if recipe.get('product_id'):
            instance['relations']['forProduct'] = recipe['product_id']
        if recipe.get('store_id'):
            instance['relations']['atStore'] = f"store_{recipe['store_id']}"

        # 재료
        if ingredients:
            uses = []
            for ing in ingredients:
                use = {
                    'ingredient': ing['ingredient_id'],
                }
                if ing.get('amount'):
                    use['amount'] = float(ing['amount'])
                if ing.get('unit'):
                    use['unit'] = ing['unit']
                if ing.get('pspec_id'):
                    use['pspec'] = ing['pspec_id']

                uses.append(use)

            instance['relations']['uses'] = uses

        instances.append(instance)

    return {'instances': instances}

def github_update_file(file_path: str, content: str, message: str):
    """GitHub 파일 업데이트"""
    if not GITHUB_TOKEN:
        print(f"⚠️  GITHUB_TOKEN not set, skipping GitHub update for {file_path}")
        return

    # 기존 파일 SHA 가져오기
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    sha = None
    if response.status_code == 200:
        sha = response.json()['sha']

    # 파일 업데이트
    content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')

    data = {
        "message": message,
        "content": content_b64,
        "branch": "main",
    }

    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()

    print(f"✅ Updated {file_path} on GitHub")

def main():
    """전체 export 및 GitHub 업데이트"""
    print("🚀 Supabase → 워터비 YAML export 시작\n")

    # Ingredients
    print("📦 Exporting ingredients...")
    ingredients_data = export_ingredients()
    ingredients_yaml = yaml.dump(ingredients_data, allow_unicode=True,
                                 default_flow_style=False, sort_keys=False, indent=2)
    github_update_file('instances/master/ingredients.yaml', ingredients_yaml,
                      'chore: sync ingredients from Supabase')

    # Products
    print("📦 Exporting products...")
    products_data = export_products()
    products_yaml = yaml.dump(products_data, allow_unicode=True,
                             default_flow_style=False, sort_keys=False, indent=2)
    github_update_file('instances/master/products.yaml', products_yaml,
                      'chore: sync products from Supabase')

    # Recipes (각 매장별)
    for store_id in ['wangsimni', 'mapo', 'wolgye']:
        print(f"📦 Exporting recipes for {store_id}...")
        recipes_data = export_recipes(store_id)
        recipes_yaml = yaml.dump(recipes_data, allow_unicode=True,
                                default_flow_style=False, sort_keys=False, indent=2)
        github_update_file(f'instances/master/recipes/{store_id}.yaml', recipes_yaml,
                          f'chore: sync {store_id} recipes from Supabase')

    print("\n🎉 Export complete!")

if __name__ == "__main__":
    main()
