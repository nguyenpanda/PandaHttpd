FILE_PATH=$0
DOCS_DIR=$(dirname $(realpath "$FILE_PATH"))
ROOT_DIR=$(dirname "$DOCS_DIR")

echo "Generating UML diagrams in $DOCS_DIR/uml"
mkdir -p "$DOCS_DIR/uml"

pyreverse \
    --output pdf \
    --project PandaHttpd \
    --source-roots "$ROOT_DIR/src" \
    --output-directory "$DOCS_DIR/uml" \
	--all-associated \
	--filter-mode=ALL \
	"$ROOT_DIR/src/PandaHttpd"
    