/* Decompress a WinCE ROM file/section blob (LZX page compression, win=2^16).
   usage: romfile <blobfile> <realsize> <outfile>
   blob = [u24 total][u24 pageEndOffset]*npages then page blocks;
   each block = [u32 0x10][u32 real][u32 comp][u32 real][u32 0x8d80805b] + LZX. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "mspack.h"
#include "lzx.h"
struct memfile{unsigned char*buf;size_t len,pos;};
static int m_read(struct mspack_file*f,void*b,int n){struct memfile*m=(void*)f;if(n<0)n=0;size_t a=m->len-m->pos;if((size_t)n>a)n=a;memcpy(b,m->buf+m->pos,n);m->pos+=n;return n;}
static int m_write(struct mspack_file*f,void*b,int n){struct memfile*m=(void*)f;if(m->pos+n>m->len)n=m->len-m->pos;memcpy(m->buf+m->pos,b,n);m->pos+=n;return n;}
static void*m_alloc(struct mspack_system*s,size_t n){return calloc(1,n);}
static void m_free(void*p){free(p);}
static void m_copy(void*a,void*b,size_t n){memcpy(b,a,n);}
#define PAGE 4096
/* The ROM compressor applies the LZX Intel-E8 call translation to every page
   even though the stream header's E8 flag bit is 0, so it must be undone here.
   Translation size 12000000; positions are relative to the start of each page. */
#define E8_FILESIZE 12000000
static void e8_undo(unsigned char*d,int len){
  if(len<=10) return;
  int end=len-10, cur=0;
  for(int i=0;i<end;){
    if(d[i]!=0xE8){ i++; cur++; continue; }
    int32_t abs_off=(int32_t)(d[i+1]|d[i+2]<<8|d[i+3]<<16|(uint32_t)d[i+4]<<24);
    if(abs_off>=-cur && abs_off<E8_FILESIZE){
      int32_t rel=(abs_off>=0)?abs_off-cur:abs_off+E8_FILESIZE;
      d[i+1]=rel; d[i+2]=rel>>8; d[i+3]=rel>>16; d[i+4]=rel>>24;
    }
    i+=5; cur+=5;
  }
}
static struct mspack_system sys;
static int lzxpage(unsigned char*stream,size_t slen,unsigned char*out,int outlen){
  struct memfile in={stream,slen,0},of={out,(size_t)outlen,0};
  struct lzxd_stream*lz=lzxd_init(&sys,(void*)&in,(void*)&of,16,0,4096,outlen,0);
  if(!lz)return -1;
  int r=lzxd_decompress(lz,outlen);
  lzxd_free(lz);
  return (of.pos==(size_t)outlen)?0:-2;
}
int main(int c,char**v){
  sys.read=m_read;sys.write=m_write;sys.alloc=m_alloc;sys.free=m_free;sys.copy=m_copy;
  FILE*f=fopen(v[1],"rb");fseek(f,0,2);long n=ftell(f);fseek(f,0,0);
  unsigned char*d=malloc(n);fread(d,1,n,f);fclose(f);
  long real=atol(v[2]);
  uint32_t total=d[0]|d[1]<<8|d[2]<<16;
  int npages=(total+PAGE-1)/PAGE;
  uint32_t*offs=malloc(npages*4);
  for(int k=0;k<npages;k++) offs[k]=d[3+3*k]|d[4+3*k]<<8|d[5+3*k]<<16;
  int tabend=3+3*npages;
  unsigned char*out=malloc(total+PAGE);
  size_t op=0; int start=tabend; int nfail=0;
  for(int k=0;k<npages;k++){
    int end=offs[k];
    unsigned char*blk=d+start; int blen=end-start; start=end;
    if(blen<20){fprintf(stderr,"page %d too small\n",k);nfail++;break;}
    uint32_t magic=*(uint32_t*)(blk+16);
    int pr=(total-op<PAGE)?(total-op):PAGE;
    if(magic!=0x8d80805b){ /* stored page */ memcpy(out+op,blk,pr<blen?pr:blen); op+=pr; continue; }
    if(lzxpage(blk+20, blen-20, out+op, pr)!=0){fprintf(stderr,"lzx fail page %d\n",k);nfail++;}
    else e8_undo(out+op, pr);
    op+=pr;
  }
  FILE*g=fopen(v[3],"wb");fwrite(out,1,total,g);fclose(g);
  fprintf(stderr,"wrote %u (real %ld) npages %d\n",total,real,npages);
  return nfail?1:0;
}
