# Haptics_Gridserch
空中音波ハプティクスのグリッドサーチを統合した版です。  
研究室で開発したコードの保存のために作成しました。

##　使用技術一覧(パイソンくらい)
<!-- 以下はシールド-->
<img src="https://img.shields.io/badge/-Python-ffff00.svg?logo=python&style=popout"><img src="https://img.shields.io/badge/-Raspberrypi-C51A4A.svg?logo=raspberrypi&style=popout">
<img src="https://img.shields.io/badge/-Github-181717.svg?logo=github&style=popout"><img src="https://img.shields.io/badge/-Git-3cb371.svg?logo=git&style=popout-square">

<!--ここから説明-->
2025年前期に作成したプログラムはラズベリーパイ上でDQN、PPOの2つの強化学習アルゴリズムを使用し、8つのスピーカーで出力した40kHzの超音波を一転に収束させるための最適な位相を探索するプログラムでした。  
フィードバックを受ける部分にはラズベリーパイピコを使用し、USB(シリアルバス通信)を使用し、電圧を文字としてラズパイに送信、その後文字を数字に変換して行っています。  

このリポジトリでは、2025年後期に取り組む内容を保存しています。  
後期では前期のシステムに加え、  
超音波距離センサーをToF(Time of Fry)で実装し、グリッドサーチを使用して収束させる対象物を三次元空間上で特定するシステムを作ります。  
