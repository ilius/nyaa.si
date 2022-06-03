grep -oP '<a href="/view/[0-9]+" title="[^"]*"' top.html | sed -E 's/.* title="(.*)"/\1/g'

