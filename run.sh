mkdir -vp textures texturepacks output/base

echo Unpacking textures ...
python3 -m pzmap2dzi.texture -o "./textures/" -m 4 "./texturepacks/"
echo Unpacking textures done

echo Render pz map ...
python3 render_base.py -o "./output/base/" -t "./textures/" -m 4 -v --group-size 100 "./map/"
echo Render pz map done

echo Render grid ...
python3 render_grid.py -o "./output/grid/" -m 4 -v --cell-grid --block-grid --group-size 100 "./map/"
echo Render grid done

echo Render room ...
python3 render_room.py -o "./output/room/" -m 4 -v --group-size 100 "./map/"
echo Render room done
