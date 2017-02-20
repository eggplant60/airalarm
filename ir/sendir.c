/*
 * sendir.c
 *
 * copyright c 2016 Katsuhiko Miki All rights reserved.
 */

#include <wiringPi.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <math.h>
#include <unistd.h>
#define BUF_LEN   256

int write_pin = 0;

int Hz = 38;            // 周波数(KHz)
int duty_num = 1;       // duty比(分子)
int duty_denomi = 3;    // duty比(分母)
int unit = 26;          // ユニット長us
int duty_high = 9;      // HIGH時間
int duty_low = 17;      // LOW時間
int repeat = 1;         // 送信回数

void high(int on_time)
{
    // パルス信号に変換して送信
    int i;
    int count = on_time/unit;
    for(i=0; i<count; i++)
    {
        digitalWrite(write_pin, 1); //high
        delayMicroseconds(duty_high);
        
        digitalWrite(write_pin, 0); //low
        delayMicroseconds(duty_low);
    }
}

void output(int on_time, int off_time)
{
    // 赤外線点灯
    high(on_time);
    
    // 赤外線消灯
    digitalWrite(write_pin, 0);
    delayMicroseconds(off_time);
}

void readAndSend(FILE *fp)
{
    char buf[BUF_LEN];
    int i, j, length = 0;
    int *on, *off;
    
    while( fgets(buf, BUF_LEN, fp) != NULL){ length++; }
    on = (int *)calloc(length, sizeof(int));
    off = (int *)calloc(length, sizeof(int));
    
    rewind(fp);
    for(i=0; i<length; i++)
    {
        fscanf(fp,"%d %d", &on[i], &off[i]);
    }
    
    // 送信(同じ情報をrepeat回送信する)
    for(j=0; j<repeat; j++)
    {
        printf("send data.\n");
        for(i=0; i<length; i++)
        {
            output(on[i], off[i]);
        }
        usleep(50000);
    }
    
    // アロケートしたメモリを解放
    free(on);
    free(off);
}

int main(int argc, char *argv[])
{
    // 送信データファイル
    FILE *fp;
    char *fileName = "irdata.txt";
    if(argc >= 2){ fileName = argv[1]; }
    if((fp = fopen(fileName, "r")) == NULL){
        printf("can't open file: %s\n", fileName);
        exit(1);
    }
    printf("read file: %s\n", fileName);
    
    // wiringpiのセットアップ
    if(wiringPiSetup() == -1){
        printf("error wiringPi setup\n");
        exit(1);
    }

    // 送信繰り返し回数
    if(argc >= 3){
        repeat = atoi(argv[2]);
    }
    
    // 送信ピン番号
    if(argc >= 4){
        write_pin = atoi(argv[3]);
    }
    pinMode(write_pin, OUTPUT);
    printf("output pin: %d (wiringpi)\n", write_pin);
    
    // 周波数の設定
    if(argc >= 5){ Hz = atoi(argv[4]); }
    
    // duty比の分子
    if(argc >= 6){ duty_num = atoi(argv[5]); }
    
    // duty比の分母
    if(argc >= 7){ duty_denomi = atoi(argv[6]); }

    // unit長
    unit = (1.0f / (Hz * 1000)) * 1000000;
    duty_high = roundf(((float)unit / duty_denomi) * duty_num);
    unit = (int)unit;     //us
    duty_low = unit - duty_high;

    printf("unit: %dms duty:%d-%d\n", unit, duty_high, duty_low);
    
    // 準備完了
    printf("send infrared signal.\n");
    
    // データ読み込みと赤外線の送信
    readAndSend(fp);

    printf("\ndone\n");
    fclose(fp);

    return 0;
}
