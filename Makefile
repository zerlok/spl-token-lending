SOLANA_URL ?= https://api.devnet.solana.com
SOL_AIRDROP_AMOUNT ?= 0.1
SOL_AIRDROP_RETRY ?= 5

SOLANA_DIR ?= $(PWD)/.local/solana

SOLANA_MINT_AMOUNT ?= 42
SOLANA_TRANSFER_AMOUNT ?= 17

USERS := alice bob
FILES := config.yml key.json token token-mint-account

OBJECTS := $(foreach u,$(USERS),$(foreach f,$(FILES),$(SOLANA_DIR)/$(u)/$(f)))


.PHONY: seed
seed: $(OBJECTS)

.PHONY: info
info:
	for u in $(USERS); do \
  		cfg="-C $(SOLANA_DIR)/$${u}/config.yml"; \
  		address=$$(solana $$cfg address); \
  		echo "user: '$${u}', address: '$${address}'"; \
  		echo "user info:"; \
  		solana $$cfg account $${address}; \
  		echo "user token info:"; \
  		spl-token $$cfg accounts; \
  	done

.PHONY: transfer-to-bob
transfer-to-bob:
	spl-token -C $(SOLANA_DIR)/alice/config.yml transfer --fund-recipient $$(cat $(SOLANA_DIR)/alice/token) $(SOLANA_TRANSFER_AMOUNT) $$(solana -C $(SOLANA_DIR)/bob/config.yml address)

.PHONY: transfer-to-alice
transfer-to-alice:
	spl-token -C $(SOLANA_DIR)/bob/config.yml transfer --fund-recipient $$(cat $(SOLANA_DIR)/alice/token) $(SOLANA_TRANSFER_AMOUNT) $$(solana -C $(SOLANA_DIR)/alice/config.yml address)

.PHONY: clean
clean:
	-rm -f $(OBJECTS)

$(SOLANA_DIR):
	mkdir -p $@

$(SOLANA_DIR)/%/config.yml: $(SOLANA_DIR)
	mkdir -p $(shell dirname $@)
	solana -C $@ config set --url $(SOLANA_URL)
	solana -C $@ config set --keypair $(shell dirname $@)/key.json

$(SOLANA_DIR)/%/key.json: $(SOLANA_DIR)/%/config.yml
	solana-keygen -C $(shell dirname $@)/config.yml new -f --no-bip39-passphrase -s -o $(shell dirname $@)/key.json
	until solana -C $(shell dirname $@)/config.yml airdrop $(SOL_AIRDROP_AMOUNT) $$(solana -C $(shell dirname $@)/config.yml address); do echo "Waiting for $(SOL_AIRDROP_RETRY) seconds ..."; sleep $(SOL_AIRDROP_RETRY); done

$(SOLANA_DIR)/%/token: $(SOLANA_DIR)/%/key.json
	spl-token -C $(shell dirname $@)/config.yml create-token | grep "Creating token" | cut -d' ' -f3 > $@
	spl-token -C $(shell dirname $@)/config.yml supply $$(cat $@)

$(SOLANA_DIR)/%/token-mint-account: $(SOLANA_DIR)/%/token
	spl-token -C $(shell dirname $@)/config.yml create-account $$(cat $(shell dirname $@)/token) | grep "Creating account" | cut -d' ' -f3 > $@
	spl-token -C $(shell dirname $@)/config.yml mint $$(cat $(shell dirname $@)/token) $(SOLANA_MINT_AMOUNT)
