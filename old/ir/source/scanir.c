/*
 * scanir.c
 * 
 * copyright c 2016 Katsuhiko Miki All rights reserved.
 */

#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <sys/time.h>

int readable = 1;       // 非同期でイベントが発生した場合、コールバックにより0に設定される
int read_pin = 7;       // 入力ピン番号(wiringpiの番号)
int interval = 10;      // 継続時間判定の間隔(us)
int max_wait = 40000;   // 最大継続時間(us)
 
void signalCallBackHandler(int sig)
{
    readable = 0;
}

double getMoment()
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    return ((double)(tv.tv_sec) * 1000000 + (double)(tv.tv_usec));
}

int main(int argc, char *argv[])
{
    int result;
    
    // スキャンデータを書きだすファイルのポインタを取得
    FILE *fp;
    char *fileName = "irdata.txt";
    if(argc >= 2){ fileName = argv[1]; }
    if((fp = fopen(fileName, "w")) == NULL){
        printf("can't open file : %s\n", fileName);
        exit(1);
    }
    printf("write file: %s\n", fileName);

    // signal関数は、シグナル(非同期イベント)が発生したときに、
    // そのシグナルを受信して、シグナル特有の処理を行うシグナル処理関数(シグナルハンドラ)を登録します。
    if(signal(SIGINT, signalCallBackHandler) == SIG_ERR){
        printf("can't set signal\n");
        exit(1);
    }

    // wiringpiのセットアップ
    if(wiringPiSetup() == -1){
        printf("error wiringPi setup\n");
        exit(1);
    }

    // 読み取りピン番号
    if(argc >= 3){
        read_pin = atoi(argv[2]);
    }
    pinMode(read_pin, INPUT);
    printf("scaning pin: %d (wiringpi)\n", read_pin);
    
    // 最大継続時間
    if(argc >= 4){
        max_wait = atoi(argv[3]) * 1000;
    }
    printf("max keep time: %d(ms)\n", max_wait/1000);

    // 準備完了
    printf("Infrared LED scanning start.\n");
    printf("Pressed Ctrl+C, this program will exit.\n");

    // スキャン開始
    result = scan(fp);
    
    fclose(fp);
    
    if(result || !readable){
        printf("\n\n!!! could not scanning. quit.\n\n");
    } else {
        printf("\nScanning has been done.\n\n");
    }

    return 0;
}

int scan(FILE *fp)
{
    // 受光モジュールは受光するとLOWになる
    if(!digitalRead(read_pin)){ return 1; }
    
    int on, off;
    
    // 送信が開始されるまで待機
    while( readable && digitalRead(read_pin) ){}
    
    // 解析開始
    while( readable ){
        on = getTime(0);
        off = getTime(1);
        fprintf(fp, "%6d %6d\n", on, off);

        //最大継続時間同じ状態が続いたら送信は終了していると判断
        if(off > max_wait){ break; }
    }

    return 0;
}

int getTime(int status)
{
    int count = 0;
    int max = max_wait / interval;
    double start, end;

    start = getMoment();
    while( digitalRead(read_pin) == status )
    {
        delayMicroseconds(interval);
    	count++;
        //最大継続時間同じ状態が続いたら送信は終了していると判断
    	if(count > max){ break; }
    }
    end = getMoment();

    return getInterval(start, end);
}

int getInterval(double t1, double t2)
{
    return (int)(t2-t1);
}
