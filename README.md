# Luft-Workspace

## Fluxo de Trabalho Git (Homologação)

O fluxo padrão para desenvolvimento e deploy em homologação é o seguinte:

1. **Crie a branch da sua feature**:
   ```powershell
   git checkout -b feature/nome-da-sua-feature
   ```
2. **Adicione as alterações e faça o commit**:
   ```powershell
   git add .
   git commit -m "feat: descrição clara da sua alteração"
   ```
   *(Atenção: Não esqueça do `-m` para a mensagem do commit!)*
3. **Envie a branch para o repositório remoto**:
   ```powershell
   git push -u origin feature/nome-da-sua-feature
   ```
4. **Abra o Pull Request (PR)**:
   - Vá ao GitHub e clique em "Compare & pull request".
   - **MUITO IMPORTANTE:** Altere a branch base (base branch) de `main` para `homologacao`.
   - Conclua a criação do PR.