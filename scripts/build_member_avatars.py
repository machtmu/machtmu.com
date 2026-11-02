#!/usr/bin/env python3
"""Verify published portrait masters or regenerate from an explicit source manifest.

Identity comes from named source text or explicit user attribution, not face matching.
Public metadata/masters suffice for CI and HTML regeneration; acquisition recipes
remain outside the published repository. Explicitly authorized edited sources are
marked and pixel-checked against that artifact, not the original. CSS handles framing.
"""
import hashlib
import argparse
import html
import json
import re
import shutil
import tempfile
from pathlib import Path

from PIL import Image, ImageOps
from build_team_profile_links import CARD_PATTERN, span_content_range


ROOT = Path(__file__).resolve().parents[1]
LEGACY_AVATARS = [{'name': 'Balin Moher', 'output': 'docs/assets/images/former-members/balin-moher-profile.webp'},
 {'name': 'Zak Harrison', 'output': 'docs/assets/images/former-members/zak-harrison-profile.webp'},
 {'name': 'Farhan Raza', 'output': 'docs/assets/images/former-members/farhan-raza-profile.webp'},
 {'name': 'Daniel Ibanescu', 'output': 'docs/assets/images/former-members/daniel-ibanescu-profile.webp'},
 {'name': 'Antonella Ruta', 'output': 'docs/assets/images/former-members/antonella-ruta-profile.webp'},
 {'name': 'David Machuca', 'output': 'docs/assets/images/former-members/david-machuca-profile.webp'},
 {'name': 'Matthew Ho', 'output': 'docs/assets/images/former-members/matthew-ho-profile.webp'},
 {'name': 'Rochelle Suarez-Tapanes',
  'output': 'docs/assets/images/former-members/rochelle-suarez-tapanes-profile.webp'}]


NATIVE_AVATARS = [{'name': 'Balin Moher',
  'sha256': '5ed02ed08e7810aa1312bc1c0329ce9db48b33f8e3562357a244a6c88aeb4600',
  'source_page': 'https://ca.linkedin.com/in/balinmoher',
  'output': 'docs/assets/images/former-members/balin-moher-native-5ed02ed08e78.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '4e7a5203baea29a35e211b5c678b5ab561a3c35ce03b0fa441b7e825831f4688',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Zak Harrison',
  'sha256': '8e6f67cfeae75f5ff69daf57f75b933ce160c58e72a5be37b6997a11008d35f6',
  'source_page': 'https://www.launchcanada.org/about',
  'output': 'docs/assets/images/former-members/zak-harrison-native-8e6f67cfeae7.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'f97628dc02142cdbe17631b79a44fba7dfa5086a4537d71a26cef7744bf08e95',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Farhan Raza',
  'sha256': '3969b9153586970e4e2984edb7e19790a981ca757c5411a42bae456189077f43',
  'source_page': 'https://www.linkedin.com/in/sfraza7',
  'output': 'docs/assets/images/former-members/farhan-raza-native-3969b9153586.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'ac3f90d6566ae1a8cd69e7023e14c162435ebde88b9880ab79f803a7ed99d115',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Daniel Ibanescu',
  'sha256': '07483c28ae3208acff2b9d4ad74ef0900b4ddd770b191888f68875046231a3d0',
  'source_page': 'https://ca.linkedin.com/in/d-ibanescu',
  'output': 'docs/assets/images/former-members/daniel-ibanescu-native-07483c28ae32.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '48550db7deb1e564c50d9e06c51169f945c8c6bdf8f15c967f33fb42b1a6ebb1',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Antonella Ruta',
  'sha256': '08a1df7c581c4b496c7914962b742124fe202b2d6f50c35105e1de1f2053d957',
  'source_page': 'https://ca.linkedin.com/in/antonella-ruta',
  'output': 'docs/assets/images/former-members/antonella-ruta-native-08a1df7c581c.webp',
  'source_dimensions': [560, 560],
  'pixel_sha256': '09c192610ea4c6e69667a319134ca0fe12a8a3edde62cb33dde5321090a0daa3',
  'frame': 'antonella',
  'source_kind': 'verified_public_portrait'},
 {'name': 'David Machuca',
  'sha256': '86f0a8eed6b754178dd032912ab8bb216dd80d5c0f33606a05a4a1fb7d61c2ef',
  'source_page': 'https://www.linkedin.com/in/david-machuca-905a0315b/',
  'output': 'docs/assets/images/former-members/david-machuca-native-86f0a8eed6b7.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '6bfae087fd90d1a5dc6a17a2725c0277b7fe3ee86450d112d5ee0d99f3133370',
  'frame': 'david',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Matthew Ho',
  'sha256': 'c782491e2e2daea888f32fa09088310a7167126164a194e7897c38d16d5729fa',
  'source_page': 'https://ca.linkedin.com/in/m1ho',
  'output': 'docs/assets/images/former-members/matthew-ho-native-c782491e2e2d.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'd5f23b84228961aaca4123c588b170b427af18cc48574c41b4b7438a88886203',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Rochelle Suarez-Tapanes',
  'sha256': '2f64697d767696c79a8b3999480361e753e6e43e671374a26e9368a7f6b31659',
  'source_page': 'https://ca.linkedin.com/in/rochelle-st',
  'output': 'docs/assets/images/former-members/rochelle-suarez-tapanes-native-2f64697d7676.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '1929ae2991cbf08e599d3e8462023976da9eae6debc10c9d2572ea5191423ff7',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Aditya Shinde',
  'sha256': 'd13a4ea54bbf0745000b2c2053ea2fd43612a44064e9c938a619bfaf7f907f70',
  'source_page': 'https://www.linkedin.com/in/adityapshinde/',
  'identity_source': 'https://github.com/machtmu/machtmu.com/blob/56da4940aef52174e9c1d33dc9c46b86710006ce/docs/leads.md',
  'output': 'docs/assets/images/former-members/aditya-shinde-native-d13a4ea54bbf.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'f7601642c5c40a05a1da2c6e554485e34707fe57bab8bbf95aa3b598dc085950',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Anuja Thurairajah',
  'sha256': 'c523eb6ac83edb7457a2fa4016622b17a04e86d3cf6c20518a40ee29c6327e11',
  'source_page': 'https://www.linkedin.com/in/anuja-thurairajah-7b1a11290/',
  'identity_source': 'https://github.com/machtmu/machtmu.com/blob/56da4940aef52174e9c1d33dc9c46b86710006ce/docs/leads.md',
  'output': 'docs/assets/images/former-members/anuja-thurairajah-native-c523eb6ac83e.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '3f6ef48e9dbbebc86274e4ec3a68fe474fef9c4ccc917f7fdcda7a90569d056b',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Adam Oudeh',
  'sha256': 'bffe60f1e10227f8ddb18cc23d066b558fa8ad20f320d4b8f4d63b2c793be670',
  'source_page': 'https://ca.linkedin.com/in/adam-oudeh',
  'output': 'docs/assets/images/former-members/adam-oudeh-native-bffe60f1e102.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'a2aa9fccae923e1a9383e5ff57222f43bce32a79060197e01a4b84eadb92e5cd',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Ben Kubica',
  'sha256': '12634fb7eaeafad1177f75bc06737ae525ce1a474689179a52da8d03145861e9',
  'source_page': 'https://ca.linkedin.com/in/ben-kubica-9ab3912bb',
  'output': 'docs/assets/images/former-members/ben-kubica-native-12634fb7eaea.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'dc442fa4622e97883e5bcc98e6d6e37acb8256a4fad12b869b1797cbdb62850a',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Jack Sinclair',
  'sha256': '457fc0ad0581c7d8e758cca26b4eba474f2b8dc2d1e4f0a1598e390243409c85',
  'source_page': 'https://ca.linkedin.com/in/sin-clair',
  'output': 'docs/assets/images/former-members/jack-sinclair-native-457fc0ad0581.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'e6f3b174dc5d11d20dc141f5f6ef0d560f1ad617c82d47a090f377e6e7e752cc',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Juliano Sciabbarrasi',
  'sha256': 'f1f17555857149a59cf1a34ae945bf98f7f97aa1f365eddf05a475e5ddbe80f5',
  'source_page': 'https://ca.linkedin.com/in/juliano-sciabbarrasi-000b74291',
  'output': 'docs/assets/images/former-members/juliano-sciabbarrasi-native-f1f175558571.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '5efa0b73beab2013ed8c6b800d766bd5bc2578bba3b245dba81a6887d0ff998b',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Kai Stewart',
  'sha256': '15ace15dcbf057279a904b8fe006688072d9b7e09abcc38a4f6343270401e3b1',
  'source_page': 'https://ca.linkedin.com/in/kai-st',
  'output': 'docs/assets/images/former-members/kai-stewart-native-15ace15dcbf0.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'fbae4f26d97969e760354da042a865a3c080852a1e5cdab2ed1aaa383a947d3f',
  'frame': 'kai',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Leandro Tomarchio',
  'sha256': 'f268d028c84d53f8122a7fb274ffb62ceb9c237892a9495f8e3f5c85509d7366',
  'source_page': 'https://ca.linkedin.com/in/leandro-tomarchio',
  'output': 'docs/assets/images/former-members/leandro-tomarchio-native-f268d028c84d.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'e5531d206dc11f3446c8bde1e0c4d7a6583a0825ce6f4760236a0998c54e99a1',
  'frame': 'leandro',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Mark Paul',
  'source_kind': 'user_authorized_ai_edit',
  'sha256': '24482cb8869398f57913582ed77986a0ca37c990fa533c31b07fa5a1b4242452',
  'source_page': 'https://ca.linkedin.com/in/mark-paul',
  'original_output_pixel_sha256': 'b8005accc4dff3ef5a4dd7cb91f05c4fe5917637225e88d156371404214a97c4',
  'output': 'docs/assets/images/former-members/mark-paul-edited-24482cb88693.webp',
  'source_dimensions': [1254, 1254],
  'pixel_sha256': '88a51f56661f0ad624c949ea23eadc5e36ec89a36df87ddaa3471b979240b950',
  'frame': 'mark'},
 {'name': 'Nikolai Sydorenko',
  'sha256': '4d07daa13390d7abf49b00f609f9872a3cf21c79c9276909b7f21da316b56f52',
  'source_page': 'https://ca.linkedin.com/in/nikolai-sydorenko',
  'output': 'docs/assets/images/former-members/nikolai-sydorenko-native-4d07daa13390.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'f28f9d6671eec69ee878ff7d23acbc9ef9204e1466664f6f34852bcd24ce6d0e',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Rui Fernandes',
  'sha256': '2fbfa5ffbbe5a82ef9aef38061ff659e15e38e635482a2099406979f7280344b',
  'source_page': 'https://ca.linkedin.com/in/rui-fernandes-55997a189',
  'output': 'docs/assets/images/former-members/rui-fernandes-native-2fbfa5ffbbe5.webp',
  'source_dimensions': [634, 634],
  'pixel_sha256': '3dd704cfb1a85e40c3c7d89ac8acd31ae126cc39a6061139bc85e9564b6f7c17',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Shivesh Maraj',
  'sha256': '8d1103160983543b8ca1ac20e1bb726a42dda060ef5bcf12deb9d1018b3bd492',
  'source_page': 'https://ca.linkedin.com/in/shivesh-maraj-55b983200',
  'output': 'docs/assets/images/former-members/shivesh-maraj-native-8d1103160983.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': 'c1c22fa8743958ceb2f389a9191d50e2962f15b0e39e66794977bb5965a612b1',
  'frame': 'shivesh',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Umar Shabbir',
  'sha256': '457726d7b9517450b3caba4b4610abdcb21aca056c58d24b2cde4ad214c76913',
  'source_page': 'https://ca.linkedin.com/in/umaremshabbir',
  'output': 'docs/assets/images/former-members/umar-shabbir-native-457726d7b951.webp',
  'source_dimensions': [450, 450],
  'pixel_sha256': 'd694d2f08a59cc40bcc823bdd53932adb53c92f74d8c00be3384fe209ddc6e69',
  'source_kind': 'verified_public_portrait'},
 {'name': 'William Pirie',
  'sha256': 'c286f5f359100bfc57b07c8a7cdab0a41bb22e98bff7c35e3b4f043058e71e1d',
  'source_page': 'https://ca.linkedin.com/in/william-pirie-25b8b31a9',
  'output': 'docs/assets/images/former-members/william-pirie-native-c286f5f35910.webp',
  'source_dimensions': [800, 800],
  'pixel_sha256': '555dbe2aabab23edffea4053e939ee70048b8275221f1943ad319affc96b9449',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Zeul Mordasiewicz',
  'sha256': '357e50d98e8c30c2dc3879f839a89ba9931dce352b8b2cdc8179b4a0425f9df5',
  'source_page': 'https://zeuldocs.com/',
  'image_url': 'https://zeuldocs.com/img/portrait.jpg',
  'output': 'docs/assets/images/former-members/zeul-mordasiewicz-native-357e50d98e8c.webp',
  'source_dimensions': [600, 600],
  'pixel_sha256': '3ef0721233c669b4db0d598bd1f49f55e6566f4faf297eb9b0c7d7cc508a7b5b',
  'source_kind': 'verified_public_portrait'},
 {'name': 'Evan Bhogal',
  'sha256': 'c0056c4e2603782acf60c7effd3f659ef4e66a4174198776aaf38b7a99e644b9',
  'output': 'docs/assets/images/former-members/evan-bhogal-native-c0056c4e2603.webp',
  'source_dimensions': [1440, 1920],
  'pixel_sha256': '6404fc6d916226a0ea0485125fe67b3225d5ba2302e313855c1e3d8173c25e65',
  'frame': 'evan-attachment',
  'source_kind': 'user_supplied'},
 {
   "name": "Georgia Jovanovic",
   "sha256": "07fe6dbdd7dc9fbd121f487f5f2629e16c71fb59b293f6a0335067818e5af489",
   "source_page": "https://machtmu.com/resources/MACH%20-%20Sponsorship%20Package%202022-2023.pdf#page=5",
   "source_kind": "verified_public_pdf_portrait",
   "output": "docs/assets/images/former-members/georgia-jovanovic-native-07fe6dbdd7dc.webp",
   "source_dimensions": [
     186,
     279
   ],
   "pixel_sha256": "73c2090558a74529a04f17d7be6e82d29d35c5e20c6fdb0bbd4888cecebbe259",
   "pdf_sha256": "473e125ddff2566faaa0f61a92fc68144d5410a3c922286369f5bbe75dc0d628",
   "pdf_page": 5,
   "pdf_image_xref": 54,
   "pdf_image_resource": "Im2",
   "embedded_image_sha256": "0acee43f3751268cec8470eec8a084535e43341c8fe713450278d6405edf9418",
   "source_color_space": "DeviceCMYK",
   "conversion": "native-dimension sRGB conversion"
 },
 {
   "name": "Yiwei Luo",
   "sha256": "f13032651589aec44f050e69ecbd9bbd370b8449325a9b4ac3d879bdc9943db2",
   "source_page": "https://machtmu.com/resources/MACH%20-%20Sponsorship%20Package%202022-2023.pdf#page=5",
   "source_kind": "verified_public_pdf_portrait",
   "output": "docs/assets/images/former-members/yiwei-luo-native-f13032651589.webp",
   "source_dimensions": [
     265,
     259
   ],
   "pixel_sha256": "86697c7495421e79e183c84c763a117b77ae97de1436585f3eba0fb94f8eb04a",
   "pdf_sha256": "473e125ddff2566faaa0f61a92fc68144d5410a3c922286369f5bbe75dc0d628",
   "pdf_page": 5,
   "pdf_image_xref": 59,
   "pdf_image_resource": "Im6",
   "embedded_image_sha256": "3777ee8f17a407a8619a384e5482746f767cf664c508a467e0a172d1f1be1f3c",
   "source_color_space": "DeviceCMYK",
   "conversion": "native-dimension sRGB conversion"
 },
 {'name': 'Orion Moore',
  'sha256': '5fc2361957fc42482b436b416c1f4b0cd9413bbde58742e5c7ec191f647712d8',
  'source_page': 'https://ontherecordnews.ca/ryerson-student-team-on-track-to-complete-new-rocket/',
  'image_url': 'https://s38612.pcdn.co/wp-content/uploads/2020/10/FB-leads-post-1-1.png',
  'identity_source': 'https://www.torontomu.ca/zone-learning/design-fabrication-zone/community/members/mach/',
  'source_attribution': 'RPG team-leads poster, courtesy of Ryerson Propulsion Group; caption: Orion M. - Combustion Dynamics Lead',
  'output': 'docs/assets/images/former-members/orion-moore-native-5fc2361957fc.webp',
  'source_dimensions': [940, 788],
  'pixel_sha256': 'b5641c957e7d8a83e5ff81feffa42fc6d40c6aa5694f409e8b26d972e65bcab7',
  'frame': 'orion-poster',
  'source_kind': 'verified_public_captioned_poster'},
 {'name': 'Maheer K.',
  'sha256': '5fc2361957fc42482b436b416c1f4b0cd9413bbde58742e5c7ec191f647712d8',
  'source_page': 'https://ontherecordnews.ca/ryerson-student-team-on-track-to-complete-new-rocket/',
  'image_url': 'https://s38612.pcdn.co/wp-content/uploads/2020/10/FB-leads-post-1-1.png',
  'identity_source': 'https://ca.linkedin.com/in/7mkazi7',
  'source_attribution': 'RPG team-leads poster, courtesy of Ryerson Propulsion Group; caption: Maheer K. - Transfer & Control Lead',
  'output': 'docs/assets/images/former-members/orion-moore-native-5fc2361957fc.webp',
  'source_dimensions': [940, 788],
  'pixel_sha256': 'b5641c957e7d8a83e5ff81feffa42fc6d40c6aa5694f409e8b26d972e65bcab7',
  'frame': 'maheer-poster',
  'source_kind': 'verified_public_captioned_poster'}]


# Active records override only their matching legacy portrait; old assets remain.
AVATARS = list({p['name']: p for p in [*LEGACY_AVATARS, *NATIVE_AVATARS]}.values())


def render_document(document):
    """Replace picture markup only; names, summaries and links stay byte-identical."""
    people = {p['name']: p for p in NATIVE_AVATARS}
    seen = set()

    def replace(match):
        body = match['body']
        name = html.unescape(re.search(r'<strong>(.*?)</strong>', body)[1])
        if name not in people:
            return match[0]
        assert name not in seen
        seen.add(name)
        entry = people[name]
        width, height = entry['source_dimensions']
        image = ('<img loading="lazy" decoding="async" class="former-member-avatar" src="/'
                 + entry['output'].removeprefix('docs/') + '" alt="" width="' + str(width)
                 + '" height="' + str(height) + '" data-display-original>')
        if entry.get('frame'):
            image = '<span class="former-member-avatar-frame former-member-avatar-frame--' + entry['frame'] + '">' + image + '</span>'
        start, _ = span_content_range(body, 'former-member-portrait')
        end = body.index('<span class="former-member-overlay">', start)
        return '<div class="former-member-card">' + body[:start] + image + body[end:] + '</div>'

    result = CARD_PATTERN.sub(replace, document)
    assert seen == people.keys()
    return result


def verify_native_output(entry, output=None):
    output = ROOT / entry['output'] if output is None else output
    with Image.open(output) as encoded:
        assert list(encoded.size) == entry['source_dimensions'], f"Native dimensions changed: {entry['name']}"
        assert hashlib.sha256(encoded.convert('RGBA').tobytes()).hexdigest() == entry['pixel_sha256'], \
            f"Decoded native pixels changed: {entry['name']}"


def build(names=None, check=False, entries=None):
    entries = [p for p in (NATIVE_AVATARS if entries is None else entries) if not names or p['name'] in names]
    if names:
        assert {p['name'] for p in entries} == set(names)
    legacy_outputs = {p['output'] for p in LEGACY_AVATARS}
    for entry in entries:
        if 'source' not in entry:
            assert check, 'Original regeneration requires --manifest with reviewed source recipes; use --check to verify published masters'
            verify_native_output(entry)
            print(f"{entry['name']}: published master verified without original-source files")
            continue
        source = ROOT / entry['source']
        before = hashlib.sha256(source.read_bytes()).hexdigest()
        assert before == entry['sha256'], f"Source changed: {entry['name']}"
        output = ROOT / entry['output']
        assert entry['output'] not in legacy_outputs and source.resolve() != output.resolve()
        if output.exists():
            verify_native_output(entry, output)
            print(f"{entry['name']}: existing native copy verified; no overwrite")
            continue
        assert not check, f"Missing native copy: {entry['name']}"
        with Image.open(source) as opened:
            photo = ImageOps.exif_transpose(opened).convert('RGBA')
            assert list(photo.size) == entry['source_dimensions']
            assert hashlib.sha256(photo.tobytes()).hexdigest() == entry['pixel_sha256']
            # Format-only, full native pixels. No crop, resize, sharpening or AI.
            photo.save(output, 'WEBP', lossless=True, quality=100, method=6, exact=True,
                       icc_profile=opened.info.get('icc_profile', b''))
        verify_native_output(entry, output)
        assert hashlib.sha256(source.read_bytes()).hexdigest() == before
        print(f"{entry['name']}: native {photo.width}x{photo.height}, {output.stat().st_size} bytes; original retained")


def warm_cache(entries):
    """Encode only reviewed image variants; never mutate the live site tree."""
    from prepare_site import Media
    with tempfile.TemporaryDirectory(prefix='mach-native-cache-') as directory:
        stage = Path(directory)
        media = Media(stage, ROOT / '.cache/media')
        for entry in entries:
            verify_native_output(entry)
            source = ROOT / entry['output']
            staged = stage / source.name
            shutil.copyfile(source, staged)
            media.variants('/' + staged.name, stage / 'index.html', portrait=True)
            print(f"{entry['name']}: responsive cache warmed; live preview unchanged", flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', action='append', dest='names')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--print', action='store_true', dest='print_document')
    parser.add_argument('--manifest', type=Path,
                        help='Private, independently accepted source recipes to stage without changing active cards')
    parser.add_argument('--warm-cache', action='store_true')
    args = parser.parse_args()
    entries = NATIVE_AVATARS
    if args.manifest:
        manifest = json.loads(args.manifest.read_text())
        assert manifest['review_status'] == 'accepted'
        entries = manifest['portraits']
    if args.print_document:
        assert not args.manifest, 'Merge accepted recipes explicitly before rendering public cards'
        print(render_document((ROOT / 'docs/team.md').read_text()), end='')
    else:
        build(args.names, args.check, entries)
        if args.warm_cache:
            warm_cache([p for p in entries if not args.names or p['name'] in args.names])
        if args.check and not args.manifest:
            source = (ROOT / 'docs/team.md').read_text()
            assert render_document(source) == source, 'Native photo source differs; apply a reviewed patch'
