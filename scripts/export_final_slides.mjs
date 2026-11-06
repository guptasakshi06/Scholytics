// Local export of the same builder used by Artifact Session, using bundled authoring tools.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {buildSlides} from './build_final_slides.mjs';
const root=path.dirname(path.dirname(fileURLToPath(import.meta.url)));
const runtime=process.env.SCHOLARREADY_NODE_MODULES;
const skill=process.env.SCHOLARREADY_PRESENTATION_SKILL;
const python=process.env.SCHOLARREADY_DOCUMENT_PYTHON;
if(!runtime||!skill||!python)throw new Error('Resolve authoring runtimes with load_workspace_dependencies; see docs/verification/S12.md');
process.env.RUNTIME_NODE_MODULES=runtime;
const {Presentation,PresentationFile}=await import(pathToFileURL(path.join(runtime,'@oai/artifact-tool/dist/artifact_tool.mjs')));
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')));
const build=path.join(root,'artifacts/runs/s12-slide-build');await fs.mkdir(build,{recursive:true});
const p=Presentation.create({slideSize:{width:1280,height:720}});
const spec=await buildSlides(p);
const candidatePath=path.join(build,'candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidatePath);
const result=await finalizePresentation({workspaceDir:root,candidatePath,
 finalPath:path.join(root,'output/presentation/ScholarReady_Slides.pptx'),pythonExecutable:python,
 integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit',...spec.tableSlides.flatMap(n=>['--require-native-table-slide',String(n)])],
 requiredNativeTableOwnerSlides:spec.tableSlides,requiredNativeChartOwnerSlides:[],explicitTotalSlideCount:12,
 fontPolicy:{basis:'design',families:['DejaVu Sans']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,'validation.json')});
console.log(JSON.stringify(result));
for(let i=0;i<p.slides.items.length;i++){
 const b=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(build,`slide-${i+1}.png`),new Uint8Array(await b.arrayBuffer()));
}
// PDF export uses bundled LibreOffice separately. Artifact Tool's PDF backend in
// this runtime lacks #standard-fonts/Helvetica; PPTX/PNG export is verified here.
