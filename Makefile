# ACX OMC Flywheel P0 - Makefile

.PHONY: help setup audit import plan apply destroy clean

help: ## Show this help message
	@echo "ACX OMC Flywheel P0 - Reverse Engineering Project"
	@echo "================================================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Setup the project environment
	@echo "🚀 Setting up P0 project..."
	pip install -r requirements.txt
	@echo "✅ Setup complete!"

audit: ## Run production environment audit
	@echo "🔍 Auditing production environment..."
	python scripts/audit_prod_resources.py
	@echo "✅ Audit complete! Check prod_audit_*.json"

import: ## Generate and run Terraform imports
	@echo "📥 Generating Terraform imports..."
	python scripts/generate_terraform_imports.py prod_audit_*.json
	@echo "📥 Running imports..."
	cd terraform/environments/prod && ../../scripts/terraform_imports.sh
	@echo "✅ Import complete!"

plan: ## Run Terraform plan
	@echo "📋 Running Terraform plan..."
	cd terraform/environments/prod && terraform plan

apply: ## Apply Terraform changes
	@echo "🚀 Applying Terraform changes..."
	cd terraform/environments/prod && terraform apply

destroy: ## Destroy Terraform resources (DANGER!)
	@echo "⚠️  DESTROYING TERRAFORM RESOURCES!"
	@read -p "Are you sure? Type 'yes' to continue: " confirm && [ "$$confirm" = "yes" ]
	cd terraform/environments/prod && terraform destroy

clean: ## Clean up temporary files
	@echo "🧹 Cleaning up..."
	rm -f prod_audit_*.json
	rm -f terraform_imports.sh
	rm -f terraform_config.tf
	@echo "✅ Clean complete!"

status: ## Show Terraform status
	@echo "📊 Terraform Status:"
	cd terraform/environments/prod && terraform state list
