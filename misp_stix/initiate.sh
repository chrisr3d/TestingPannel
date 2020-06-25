if [ -z "$1" ]; then
    destination="/var/www/MISP/app/files/scripts/stixtest/"
else
    destination=$1
fi
script_name="parse_simplified_misp_format.py"
link_name="${destination}${script_name}"
if [ -e "$link_name" ]; then
    rm $link_name
fi
ln $script_name "${link_name}"
