"""
버전 자동 업데이트 스크립트
현재 시간 기반으로 version.json을 업데이트합니다.
"""

import json
from datetime import datetime
import sys


def update_version(changelog_message=None):
    """version.json을 현재 시간 기반으로 업데이트"""
    
    # 현재 시간 기반 버전 생성 (YYYY.MM.DD.HHMM)
    now = datetime.now()
    new_version = now.strftime("%Y.%m.%d.%H%M")
    build_date = now.strftime("%Y-%m-%d")
    
    print(f"새 버전: {new_version}")
    print(f"빌드 날짜: {build_date}")
    
    try:
        # 기존 version.json 읽기
        with open('version.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        old_version = data.get('version', 'unknown')
        print(f"이전 버전: {old_version}")
        
        # 버전 업데이트
        data['version'] = new_version
        data['build_date'] = build_date
        
        # 변경사항 메시지가 있으면 changelog에 추가
        if changelog_message:
            new_changelog = {
                "version": new_version,
                "date": build_date,
                "changes": [changelog_message]
            }
            
            # 기존 changelog 앞에 추가
            if 'changelog' not in data:
                data['changelog'] = []
            data['changelog'].insert(0, new_changelog)
            
            print(f"변경사항 추가: {changelog_message}")
        
        # 파일 저장
        with open('version.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("\nversion.json 업데이트 완료!")
        print(f"   버전: {new_version}")
        print(f"   날짜: {build_date}")
        
        return new_version
        
    except Exception as e:
        print(f"오류 발생: {e}")
        sys.exit(1)


if __name__ == '__main__':
    # 커맨드라인 인자로 변경사항 메시지 받기
    changelog_msg = None
    if len(sys.argv) > 1:
        changelog_msg = ' '.join(sys.argv[1:])
    
    version = update_version(changelog_msg)
    print(f"\n태그 생성 명령어:")
    print(f"  git tag -a v{version} -m \"Release v{version}\"")
    print(f"  git push origin v{version}")

